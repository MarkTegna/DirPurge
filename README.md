# DirPurge

A Windows file management utility that automatically purges old files from target directories while preserving recent files and maintaining minimum counts per file set.

**Author:** Mark Oldham  
**Version:** 1.0.0  
**Platform:** Windows

## Features

- **Smart File Grouping**: Groups files by prefix (part before "__" delimiter)
- **Preservation Rules**: Keeps newest N files and all files younger than age threshold
- **Configurable Extensions**: Exclude specific file types from processing
- **Dry Run Mode**: Preview operations without making changes
- **Detailed Reporting**: Generate timestamped reports with operation statistics
- **Email Notifications**: Optional SMTP email reports
- **Comprehensive CLI**: Override any configuration setting via command line

## Quick Start

1. **Configure**: Edit `dirpurge.ini` with your target directory and preferences
2. **Test**: Run with `--dry-run` to preview operations
3. **Execute**: Run without dry-run to perform actual file purging

```cmd
# Preview what would be deleted
dirpurge.exe --dry-run

# Execute with custom settings
dirpurge.exe --target-directory "C:\temp\logs" --min-files 25 --max-age 180
```

## Configuration

### INI File (dirpurge.ini)

```ini
[general]
target_directory = C:\temp\purge_target
min_files_to_keep = 50
max_age_days = 366
excluded_extensions = .PL,.TXT,.CSV,.ZIP
dry_run = false
reports_directory = ./reports

[email]
send_email = false
smtp_server = smtp.gmail.com
smtp_port = 587
smtp_use_tls = true
from_email = dirpurge@company.com
to_email = admin@company.com
```

### Command Line Options

```
-t, --target-directory    Target directory to purge
-m, --min-files          Minimum files to keep per set (default: 50)
-a, --max-age            Maximum age in days (default: 366)
-e, --excluded-extensions Comma-separated extensions to exclude
-d, --dry-run            Preview mode - no actual deletion
-r, --reports-directory  Directory for reports (default: ./reports)
--send-email             Enable email notifications
--smtp-server            SMTP server hostname
--smtp-port              SMTP port (default: 25)
--smtp-tls               Use TLS for SMTP
--from-email             Email sender address
--to-email               Email recipient address
```

## How It Works

1. **File Scanning**: Scans target directory for files with "__" delimiter
2. **Grouping**: Groups files by prefix (part before "__")
3. **Filtering**: Excludes files with configured extensions
4. **Preservation**: Applies rules to determine which files to keep:
   - Keep newest N files per group (configurable)
   - Keep all files younger than age threshold (configurable)
5. **Purging**: Deletes files that exceed both preservation criteria
6. **Reporting**: Generates detailed reports and optional email notifications

## File Naming Convention

DirPurge processes files that follow this naming pattern:
```
prefix__suffix.extension
```

Examples:
- `backup__20240101.log` (prefix: "backup")
- `report__daily_summary.dat` (prefix: "report")
- `archive__user_data.zip` (prefix: "archive")

Files without "__" delimiter are ignored.

## Safety Features

- **Dry Run Mode**: Test operations without making changes
- **Preservation Rules**: Multiple criteria ensure important files are kept
- **Error Handling**: Continues processing if individual files can't be accessed
- **Detailed Logging**: Comprehensive reports of all operations
- **Configuration Validation**: Validates settings before execution

## Building from Source

### Requirements
- Python 3.8+
- PyInstaller (for building executable)

### Build Steps
```cmd
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt

# Run tests
python -m pytest

# Build executable
python build.py
```

The build process:
1. Automatically increments patch version
2. Creates Windows executable with PyInstaller
3. Packages distribution ZIP with version number

### Version Management
```cmd
# Increment patch version (automatic during build)
python increment_build.py

# Update major/minor version manually
python update_version.py 2.0.0
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions, please contact Mark Oldham.