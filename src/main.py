"""Main application entry point for DirPurge"""

import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config_manager import ConfigManager
from .file_scanner import FileScanner
from .purge_engine import PurgeEngine
from .reporter import Reporter
from .email_service import EmailService
from .error_handler import ErrorHandler
from .models import PurgeResult
from version import __version__, __author__, __compile_date__


def main(args: Optional[list] = None) -> int:
    """Main application entry point"""
    try:
        # Initialize configuration manager
        config_manager = ConfigManager()
        
        # Handle no arguments case - try to use default INI file
        if args is None:
            args = sys.argv[1:]
        
        # Parse CLI arguments (empty args is OK, we'll try INI file)
        try:
            cli_config = config_manager.parse_cli_args(args)
        except SystemExit as e:
            # argparse calls sys.exit() for --help and --version
            return e.code if e.code is not None else 0
        
        # Determine INI file path
        ini_file_path = "dirpurge.ini"  # Default
        if 'config_file' in cli_config and cli_config['config_file']:
            ini_file_path = cli_config['config_file']
            # Remove config_file from cli_config as it's not a configuration setting
            del cli_config['config_file']
        
        # Load INI configuration
        ini_config = {}
        if Path(ini_file_path).exists():
            try:
                ini_config = config_manager.load_config_from_ini(ini_file_path)
                print(f"Using configuration file: {ini_file_path}")
            except ValueError as e:
                ErrorHandler.log_error(f"INI file error: {e}")
                return 1
        elif ini_file_path != "dirpurge.ini":
            # User specified a config file that doesn't exist
            ErrorHandler.log_error(f"Configuration file not found: {ini_file_path}")
            return 1
        elif not cli_config and not ini_config:
            # No INI file and no CLI options - show help
            config_manager.parse_cli_args(['--help'])
            return 0
        
        # Merge configurations (CLI takes precedence)
        merged_config = config_manager.merge_configs(ini_config, cli_config)
        
        # Validate CLI arguments
        try:
            config_manager.validate_cli_args(merged_config)
        except ValueError as e:
            ErrorHandler.log_error(str(e))
            return 1
        
        # Create configuration object
        config = config_manager.create_config_object(merged_config)
        
        # Validate complete configuration
        config_errors = ErrorHandler.validate_configuration(config)
        if config_errors:
            ErrorHandler.log_error("Configuration validation failed:")
            for error in config_errors:
                ErrorHandler.log_error(f"  - {error}")
            return 1
        
        # Initialize components
        file_scanner = FileScanner(config.excluded_extensions)
        purge_engine = PurgeEngine(config.min_files_to_keep, config.max_age_days)
        reporter = Reporter(config.reports_directory)
        
        # Scan directory
        print(f"Scanning directory: {config.target_directory}")
        try:
            file_groups = file_scanner.scan_directory(config.target_directory)
        except ValueError as e:
            ErrorHandler.log_error(str(e))
            return 1
        
        # Calculate statistics
        total_files = sum(len(files) for files in file_groups.values())
        file_sets_found = len(file_groups)
        
        print(f"Found {total_files} files in {file_sets_found} file sets")
        
        # Determine files to purge
        files_to_delete, files_to_preserve = purge_engine.determine_files_to_purge(file_groups)
        
        print(f"Files to delete: {len(files_to_delete)}")
        print(f"Files to preserve: {len(files_to_preserve)}")
        
        if config.dry_run:
            print("DRY RUN MODE - No files will be deleted")
        
        # Execute purge
        purge_result = purge_engine.execute_purge(files_to_delete, config.dry_run)
        
        # Update result with complete information
        purge_result.total_files_scanned = total_files
        purge_result.file_sets_found = file_sets_found
        purge_result.files_preserved = files_to_preserve
        
        # Generate and save report
        report_content = reporter.generate_report(purge_result, config, file_groups)
        report_path = reporter.save_report(report_content)
        
        print(f"Report saved to: {report_path}")
        
        # Generate XLSX report if enabled
        if config.generate_xlsx:
            try:
                xlsx_path = reporter.generate_xlsx_report(file_groups)
                print(f"Excel report saved to: {xlsx_path}")
            except ImportError as e:
                print(f"Warning: Could not generate Excel report: {e}")
            except Exception as e:
                print(f"Warning: Failed to generate Excel report: {e}")
        
        # Send email if configured
        if config.email_settings and config.email_settings.send_email:
            email_service = EmailService(config.email_settings)
            email_success = email_service.send_report(report_content)
            if not email_success:
                print("Warning: Failed to send email report")
        
        # Print summary
        print("\nOperation Summary:")
        print(f"  Files scanned: {purge_result.total_files_scanned}")
        print(f"  Files deleted: {purge_result.actual_deletions}")
        print(f"  Files preserved: {len(purge_result.files_preserved)}")
        print(f"  Execution time: {purge_result.execution_time:.2f} seconds")
        
        if purge_result.errors:
            print(f"  Errors encountered: {len(purge_result.errors)}")
            for error in purge_result.errors:
                ErrorHandler.log_warning(error)
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        ErrorHandler.log_error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())