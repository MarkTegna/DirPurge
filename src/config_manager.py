"""Configuration management for DirPurge"""

import configparser
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from .models import Config, EmailConfig
from version import __version__, __author__, __compile_date__


class ConfigManager:
    """Manages configuration from INI files and CLI arguments"""
    
    def __init__(self):
        self.default_config = {
            'general': {
                'target_directory': '',
                'min_files_to_keep': '50',
                'max_age_days': '366',
                'excluded_extensions': '.PL,.TXT,.CSV,.ZIP',
                'dry_run': 'false',
                'reports_directory': './reports'
            },
            'email': {
                'send_email': 'false',
                'smtp_server': '',
                'smtp_port': '25',
                'smtp_use_tls': 'false',
                'smtp_username': '',
                'smtp_password': '',
                'from_email': '',
                'to_email': ''
            }
        }
    
    def load_config_from_ini(self, ini_path: str) -> Dict[str, Any]:
        """Load configuration from INI file with validation"""
        config_dict = {}
        
        if not Path(ini_path).exists():
            return config_dict
        
        try:
            parser = configparser.ConfigParser()
            parser.read(ini_path)
            
            # Parse general section
            if parser.has_section('general'):
                general = parser['general']
                config_dict.update({
                    'target_directory': general.get('target_directory', ''),
                    'min_files_to_keep': general.getint('min_files_to_keep', 50),
                    'max_age_days': general.getint('max_age_days', 366),
                    'excluded_extensions': self._parse_extensions(
                        general.get('excluded_extensions', '.PL,.TXT,.CSV,.ZIP')
                    ),
                    'dry_run': general.getboolean('dry_run', False),
                    'reports_directory': general.get('reports_directory', './reports')
                })
            
            # Parse email section
            email_config = None
            if parser.has_section('email'):
                email = parser['email']
                email_config = EmailConfig(
                    send_email=email.getboolean('send_email', False),
                    smtp_server=email.get('smtp_server', ''),
                    smtp_port=email.getint('smtp_port', 25),
                    smtp_use_tls=email.getboolean('smtp_use_tls', False),
                    smtp_username=email.get('smtp_username', ''),
                    smtp_password=email.get('smtp_password', ''),
                    from_email=email.get('from_email', ''),
                    to_email=email.get('to_email', '')
                )
            
            config_dict['email_settings'] = email_config
            
        except (configparser.Error, ValueError) as e:
            raise ValueError(f"Invalid INI file format: {e}")
        
        return config_dict
    
    def _parse_extensions(self, extensions_str: str) -> List[str]:
        """Parse comma-separated extensions string"""
        if not extensions_str.strip():
            return []
        return [ext.strip().upper() for ext in extensions_str.split(',')]
    
    def validate_config(self, config_dict: Dict[str, Any]) -> None:
        """Validate configuration values"""
        errors = []
        
        # Validate target directory
        if not config_dict.get('target_directory'):
            errors.append("target_directory is required")
        elif not Path(config_dict['target_directory']).exists():
            errors.append(f"Target directory does not exist: {config_dict['target_directory']}")
        
        # Validate numeric values
        if config_dict.get('min_files_to_keep', 0) < 0:
            errors.append("min_files_to_keep must be non-negative")
        
        if config_dict.get('max_age_days', 0) < 0:
            errors.append("max_age_days must be non-negative")
        
        # Validate email configuration if enabled
        email_config = config_dict.get('email_settings')
        if email_config and email_config.send_email:
            if not email_config.smtp_server:
                errors.append("smtp_server is required when email is enabled")
            if not email_config.from_email:
                errors.append("from_email is required when email is enabled")
            if not email_config.to_email:
                errors.append("to_email is required when email is enabled")
            if email_config.smtp_port <= 0 or email_config.smtp_port > 65535:
                errors.append("smtp_port must be between 1 and 65535")
        
        if errors:
            raise ValueError("Configuration validation errors:\n" + "\n".join(f"- {error}" for error in errors))
    
    def create_config_object(self, config_dict: Dict[str, Any]) -> Config:
        """Create Config object from configuration dictionary"""
        return Config(
            target_directory=config_dict.get('target_directory', ''),
            min_files_to_keep=config_dict.get('min_files_to_keep', 50),
            max_age_days=config_dict.get('max_age_days', 366),
            excluded_extensions=config_dict.get('excluded_extensions', ['.PL', '.TXT', '.CSV', '.ZIP']),
            dry_run=config_dict.get('dry_run', False),
            reports_directory=config_dict.get('reports_directory', './reports'),
            email_settings=config_dict.get('email_settings')
        )
    
    def parse_cli_args(self, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(
            prog='DirPurge',
            description='Windows file management utility that purges old files while preserving recent ones',
            epilog=f'Author: {__author__} | Version: {__version__} | Compile Date: {__compile_date__}',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # General options
        parser.add_argument(
            '-t', '--target-directory',
            dest='target_directory',
            help='Target directory to purge files from'
        )
        
        parser.add_argument(
            '-m', '--min-files',
            dest='min_files_to_keep',
            type=int,
            help='Minimum number of files to keep per file set (default: 50)'
        )
        
        parser.add_argument(
            '-a', '--max-age',
            dest='max_age_days',
            type=int,
            help='Maximum age in days for files to preserve (default: 366)'
        )
        
        parser.add_argument(
            '-e', '--excluded-extensions',
            dest='excluded_extensions',
            help='Comma-separated list of file extensions to exclude (default: .PL,.TXT,.CSV,.ZIP)'
        )
        
        parser.add_argument(
            '-d', '--dry-run',
            dest='dry_run',
            action='store_true',
            help='Preview mode - show what would be deleted without actually deleting'
        )
        
        parser.add_argument(
            '-r', '--reports-directory',
            dest='reports_directory',
            help='Directory to save reports (default: ./reports)'
        )
        
        # Email options
        parser.add_argument(
            '--send-email',
            dest='send_email',
            action='store_true',
            help='Enable email notifications'
        )
        
        parser.add_argument(
            '--smtp-server',
            dest='smtp_server',
            help='SMTP server hostname'
        )
        
        parser.add_argument(
            '--smtp-port',
            dest='smtp_port',
            type=int,
            help='SMTP server port (default: 25)'
        )
        
        parser.add_argument(
            '--smtp-tls',
            dest='smtp_use_tls',
            action='store_true',
            help='Use TLS for SMTP connection'
        )
        
        parser.add_argument(
            '--smtp-username',
            dest='smtp_username',
            help='SMTP authentication username'
        )
        
        parser.add_argument(
            '--smtp-password',
            dest='smtp_password',
            help='SMTP authentication password'
        )
        
        parser.add_argument(
            '--from-email',
            dest='from_email',
            help='Email address to send from'
        )
        
        parser.add_argument(
            '--to-email',
            dest='to_email',
            help='Email address to send to'
        )
        
        parser.add_argument(
            '-c', '--config',
            dest='config_file',
            help='Path to INI configuration file (default: dirpurge.ini)'
        )
        
        parser.add_argument(
            '--version',
            action='version',
            version=f'DirPurge {__version__} by {__author__} (compiled {__compile_date__})'
        )
        
        # Parse arguments
        parsed_args = parser.parse_args(args)
        
        # Convert to dictionary, filtering out None values
        config_dict = {}
        
        # Handle config file parameter
        if parsed_args.config_file is not None:
            config_dict['config_file'] = parsed_args.config_file
        
        # General settings
        if parsed_args.target_directory is not None:
            config_dict['target_directory'] = parsed_args.target_directory
        if parsed_args.min_files_to_keep is not None:
            config_dict['min_files_to_keep'] = parsed_args.min_files_to_keep
        if parsed_args.max_age_days is not None:
            config_dict['max_age_days'] = parsed_args.max_age_days
        if parsed_args.excluded_extensions is not None:
            config_dict['excluded_extensions'] = self._parse_extensions(parsed_args.excluded_extensions)
        if parsed_args.dry_run:
            config_dict['dry_run'] = True
        if parsed_args.reports_directory is not None:
            config_dict['reports_directory'] = parsed_args.reports_directory
        
        # Email settings - create EmailConfig if any email args are provided
        email_args = {
            'send_email': parsed_args.send_email,
            'smtp_server': parsed_args.smtp_server,
            'smtp_port': parsed_args.smtp_port,
            'smtp_use_tls': parsed_args.smtp_use_tls,
            'smtp_username': parsed_args.smtp_username,
            'smtp_password': parsed_args.smtp_password,
            'from_email': parsed_args.from_email,
            'to_email': parsed_args.to_email
        }
        
        # Only create email config if any email-related arguments were provided
        if any(value is not None and value is not False for value in email_args.values()):
            email_config = EmailConfig(
                send_email=email_args['send_email'] or False,
                smtp_server=email_args['smtp_server'] or '',
                smtp_port=email_args['smtp_port'] or 25,
                smtp_use_tls=email_args['smtp_use_tls'] or False,
                smtp_username=email_args['smtp_username'] or '',
                smtp_password=email_args['smtp_password'] or '',
                from_email=email_args['from_email'] or '',
                to_email=email_args['to_email'] or ''
            )
            config_dict['email_settings'] = email_config
        
        return config_dict
    
    def merge_configs(self, ini_config: Dict[str, Any], cli_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge INI and CLI configurations with CLI taking precedence"""
        merged = ini_config.copy()
        
        # Update with CLI values (CLI takes precedence)
        for key, value in cli_config.items():
            if key == 'email_settings':
                # Special handling for email settings
                if value is not None:
                    if merged.get('email_settings') is None:
                        merged['email_settings'] = value
                    else:
                        # Merge email settings, CLI takes precedence
                        existing_email = merged['email_settings']
                        new_email = EmailConfig(
                            send_email=value.send_email if value.send_email else existing_email.send_email,
                            smtp_server=value.smtp_server if value.smtp_server else existing_email.smtp_server,
                            smtp_port=value.smtp_port if value.smtp_port != 25 else existing_email.smtp_port,
                            smtp_use_tls=value.smtp_use_tls if value.smtp_use_tls else existing_email.smtp_use_tls,
                            smtp_username=value.smtp_username if value.smtp_username else existing_email.smtp_username,
                            smtp_password=value.smtp_password if value.smtp_password else existing_email.smtp_password,
                            from_email=value.from_email if value.from_email else existing_email.from_email,
                            to_email=value.to_email if value.to_email else existing_email.to_email
                        )
                        merged['email_settings'] = new_email
            else:
                merged[key] = value
        
        return merged
    
    def validate_cli_args(self, config_dict: Dict[str, Any]) -> None:
        """Validate CLI argument values"""
        errors = []
        
        # Validate numeric ranges
        if 'min_files_to_keep' in config_dict:
            if config_dict['min_files_to_keep'] < 0:
                errors.append("--min-files must be non-negative")
        
        if 'max_age_days' in config_dict:
            if config_dict['max_age_days'] < 0:
                errors.append("--max-age must be non-negative")
        
        # Validate email port
        email_config = config_dict.get('email_settings')
        if email_config and hasattr(email_config, 'smtp_port'):
            if email_config.smtp_port <= 0 or email_config.smtp_port > 65535:
                errors.append("--smtp-port must be between 1 and 65535")
        
        if errors:
            raise ValueError("CLI argument validation errors:\n" + "\n".join(f"- {error}" for error in errors))