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
from .error_handler import ErrorHandler, SecurityError
from .models import PurgeResult
from .logger import get_logger
from .validators import ValidationError, validate_all_inputs
from .resource_manager import ResourceManager, ResourceLimits, ResourceExhaustionError, OperationTimeoutError
from version import __version__, __author__, __compile_date__

logger = get_logger()


def main(args: Optional[list] = None) -> int:
    """Main application entry point with security enhancements"""
    resource_manager = ResourceManager(ResourceLimits())
    
    try:
        with resource_manager.operation_context("main_application"):
            logger.info("DirPurge application starting", extra={
                'version': __version__,
                'author': __author__,
                'compile_date': __compile_date__
            })
            
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
                    logger.info(f"Using configuration file: {ini_file_path}")
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
            
            # Validate all inputs with security checks
            try:
                validate_all_inputs(merged_config)
            except ValidationError as e:
                ErrorHandler.log_error(f"Input validation failed: {e}")
                return 1
            
            # Validate CLI arguments
            try:
                config_manager.validate_cli_args(merged_config)
            except ValueError as e:
                ErrorHandler.log_error(str(e))
                return 1
            
            # Create configuration object
            config = config_manager.create_config_object(merged_config)
            
            # Validate complete configuration with security checks
            config_errors = ErrorHandler.validate_configuration(config)
            if config_errors:
                ErrorHandler.log_error("Configuration validation failed:")
                for error in config_errors:
                    ErrorHandler.log_error(f"  - {error}")
                return 1
            
            # Security validation for target directory
            try:
                ErrorHandler.validate_operation_safety("scan", config.target_directory)
            except SecurityError as e:
                ErrorHandler.log_error(f"Security validation failed: {e}")
                return 1
            
            # Initialize components
            file_scanner = FileScanner(config.excluded_extensions)
            purge_engine = PurgeEngine(config.min_files_to_keep, config.max_age_days)
            reporter = Reporter(config.reports_directory)
            
            # Scan directory with resource monitoring
            logger.info(f"Scanning directory: {config.target_directory}")
            try:
                with resource_manager.timeout_context(resource_manager.limits.scan_timeout_seconds, "directory_scan"):
                    file_groups = file_scanner.scan_directory(config.target_directory)
                    
                    # Check file count limits
                    total_files = sum(len(files) for files in file_groups.values())
                    resource_manager.check_file_count_limit(total_files)
                    
            except (ValueError, ResourceExhaustionError, OperationTimeoutError) as e:
                ErrorHandler.log_error(str(e))
                return 1
            
            # Calculate statistics
            total_files = sum(len(files) for files in file_groups.values())
            file_sets_found = len(file_groups)
            
            logger.info("Scan completed", extra={
                'total_files': total_files,
                'file_sets_found': file_sets_found
            })
            
            # Periodic resource check
            resource_manager.enforce_periodic_checks()
            
            # Determine files to purge
            files_to_delete, files_to_preserve = purge_engine.determine_files_to_purge(file_groups)
            
            logger.info("Purge analysis completed", extra={
                'files_to_delete': len(files_to_delete),
                'files_to_preserve': len(files_to_preserve),
                'dry_run': config.dry_run
            })
            
            if config.dry_run:
                logger.info("DRY RUN MODE - No files will be deleted")
            
            # Execute purge with resource monitoring
            try:
                purge_result = purge_engine.execute_purge(files_to_delete, config.dry_run)
            except (ResourceExhaustionError, OperationTimeoutError) as e:
                ErrorHandler.log_error(f"Purge operation failed: {e}")
                return 1
            
            # Update result with complete information
            purge_result.total_files_scanned = total_files
            purge_result.file_sets_found = file_sets_found
            purge_result.files_preserved = files_to_preserve
            
            # Generate and save report
            report_content = reporter.generate_report(purge_result, config, file_groups)
            report_path = reporter.save_report(report_content)
            
            logger.info(f"Report saved to: {report_path}")
            
            # Generate XLSX report if enabled
            if config.generate_xlsx:
                try:
                    xlsx_path = reporter.generate_xlsx_report(file_groups)
                    logger.info(f"Excel report saved to: {xlsx_path}")
                except ImportError as e:
                    logger.warning(f"Could not generate Excel report: {e}")
                except Exception as e:
                    logger.warning(f"Failed to generate Excel report: {e}")
            
            # Send email if configured
            if config.email_settings and config.email_settings.send_email:
                try:
                    with resource_manager.timeout_context(resource_manager.limits.email_timeout_seconds, "email_send"):
                        email_service = EmailService(config.email_settings)
                        email_success = email_service.send_report(report_content)
                        if not email_success:
                            logger.warning("Failed to send email report")
                except OperationTimeoutError:
                    logger.error("Email send operation timed out")
                except Exception as e:
                    logger.error(f"Email send failed: {e}")
            
            # Final resource check and logging
            resource_manager.log_resource_status()
            
            # Print summary
            logger.info("Operation completed successfully", extra={
                'files_scanned': purge_result.total_files_scanned,
                'files_deleted': purge_result.actual_deletions,
                'files_preserved': len(purge_result.files_preserved),
                'execution_time': purge_result.execution_time,
                'errors': len(purge_result.errors) if purge_result.errors else 0
            })
            
            if purge_result.errors:
                logger.warning(f"Errors encountered: {len(purge_result.errors)}")
                for error in purge_result.errors:
                    ErrorHandler.log_warning(error)
            
            return 0
        
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        return 130
    except SecurityError as e:
        ErrorHandler.log_error(f"Security error: {e}")
        return 1
    except (ResourceExhaustionError, OperationTimeoutError) as e:
        ErrorHandler.log_error(f"Resource limit exceeded: {e}")
        return 1
    except Exception as e:
        ErrorHandler.log_error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())