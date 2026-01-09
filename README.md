# DirPurge

A production-grade Windows file management utility that automatically purges old files from target directories while preserving recent files and maintaining minimum counts per file set.

**Author:** Mark Oldham  
**Version:** 1.3.0  
**Platform:** Windows

## Features

### Core Functionality
- **Smart File Grouping**: Groups files by prefix (part before "__" delimiter)
- **Preservation Rules**: Keeps newest N files and all files younger than age threshold
- **Configurable Extensions**: Exclude specific file types from processing
- **Dry Run Mode**: Preview operations without making changes
- **Excel Reporting**: Optional XLSX export with file set summaries

### Production Features
- **Comprehensive Security**: Input validation, secure logging, threat protection
- **Health Monitoring**: System resource monitoring and health checks
- **Graceful Shutdown**: Signal handling with proper resource cleanup
- **Circuit Breakers**: Fault tolerance for external services
- **Performance Metrics**: Comprehensive metrics collection with Prometheus export
- **Resource Management**: Memory limits, timeouts, and operation constraints

### Operational Excellence
- **Structured Logging**: Security-aware logging with sensitive data filtering
- **Configuration Validation**: Schema-based validation with clear error messages
- **Dependency Injection**: Modular architecture with loose coupling
- **Comprehensive Testing**: Unit tests and property-based testing

## Architecture Overview

### Component Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Main App      │    │  Config Manager │    │  Validators     │
│                 │────│                 │────│                 │
│ - Entry Point   │    │ - INI Loading   │    │ - Input Validation
│ - Orchestration │    │ - CLI Parsing   │    │ - Security Checks
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  File Scanner   │    │  Purge Engine   │    │   Reporter      │
│                 │────│                 │────│                 │
│ - Directory Scan│    │ - File Analysis │    │ - Report Gen    │
│ - File Grouping │    │ - Purge Logic   │    │ - XLSX Export   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Resource Mgmt   │    │ Email Service   │    │ Health Monitor  │
│                 │    │                 │    │                 │
│ - Memory Limits │    │ - SMTP Client   │    │ - System Health │
│ - Timeouts      │    │ - Circuit Break │    │ - Monitoring    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Security Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Input Layer     │    │ Validation      │    │ Processing      │
│                 │────│                 │────│                 │
│ - CLI Args      │    │ - Path Validate │    │ - Safe Operations
│ - INI Files     │    │ - Input Sanitize│    │ - Resource Limits
│ - User Input    │    │ - Security Check│    │ - Error Handling
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Secure Logging  │    │ Error Handler   │    │ Audit Trail     │
│                 │    │                 │    │                 │
│ - Data Filtering│    │ - Safe Contexts │    │ - Security Events
│ - Event Logging │    │ - Threat Detect │    │ - Operation Logs
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### Basic Usage

1. **Configure**: Edit `dirpurge.ini` with your target directory and preferences
2. **Test**: Run with `--dry-run` to preview operations
3. **Execute**: Run without dry-run to perform actual file purging

```cmd
# Preview what would be deleted
dirpurge.exe --dry-run

# Execute with custom settings
dirpurge.exe --target-directory "C:\temp\logs" --min-files 25 --max-age 180

# Generate Excel report
dirpurge.exe --generate-xlsx
```

### Production Deployment

1. **Health Check**: Verify system health before operations
2. **Monitor**: Use metrics endpoint for monitoring integration
3. **Alerts**: Configure alerts based on health and performance metrics
4. **Backup**: Ensure rollback procedures are tested

## Configuration

### INI File (dirpurge.ini)

```ini
[general]
target_directory = C:\YourDirectory
min_files_to_keep = 50
max_age_days = 366
excluded_extensions = .PL,.TXT,.CSV,.ZIP
dry_run = false
reports_directory = ./reports
# generate_xlsx = true

[email]
# send_email = true
# smtp_server = smtp.yourcompany.com
# smtp_port = 25
# smtp_use_tls = false
# from_email = dirpurge@yourcompany.com
# to_email = admin@yourcompany.com
```

### Command Line Options

```
General Options:
  -t, --target-directory    Target directory to purge
  -m, --min-files          Minimum files to keep per set (default: 50)
  -a, --max-age            Maximum age in days (default: 366)
  -e, --excluded-extensions Comma-separated extensions to exclude
  -d, --dry-run            Preview mode - no actual deletion
  -r, --reports-directory  Directory for reports (default: ./reports)
  -c, --config             Path to INI configuration file
  --generate-xlsx          Generate Excel file with file set summary

Email Options:
  --send-email             Enable email notifications
  --smtp-server            SMTP server hostname
  --smtp-port              SMTP port (default: 25)
  --smtp-tls               Use TLS for SMTP
  --from-email             Email sender address
  --to-email               Email recipient address

Information:
  --version                Show version information
  -h, --help               Show help message
```

## How It Works

### File Processing Pipeline

1. **Configuration Loading**: Load and validate configuration from INI file and CLI
2. **Input Validation**: Validate all inputs for security and correctness
3. **Health Checks**: Verify system health and resource availability
4. **Directory Scanning**: Scan target directory for files with "__" delimiter
5. **File Grouping**: Group files by prefix (part before "__")
6. **Filtering**: Exclude files with configured extensions
7. **Preservation Analysis**: Apply rules to determine which files to keep
8. **Purge Execution**: Delete files that exceed preservation criteria
9. **Reporting**: Generate detailed reports and optional Excel export
10. **Notifications**: Send email notifications if configured

### File Naming Convention

DirPurge processes files that follow this naming pattern:
```
prefix__suffix.extension
```

Examples:
- `backup__20240101.log` (prefix: "backup")
- `report__daily_summary.dat` (prefix: "report")
- `archive__user_data.zip` (prefix: "archive")

Files without "__" delimiter are ignored.

### Preservation Rules

Files are preserved if they meet ANY of these criteria:
- Among the newest N files in their group (configurable)
- Younger than the maximum age threshold (configurable)
- Have an excluded file extension

## Security Features

### Input Protection
- **Path Traversal Prevention**: All paths validated against traversal attacks
- **Input Sanitization**: All user inputs sanitized before processing
- **Configuration Validation**: Schema-based validation with security checks
- **Operation Safety**: Dangerous operations blocked by default

### Secure Logging
- **Sensitive Data Filtering**: Passwords and secrets automatically redacted
- **Security Event Logging**: All security-relevant events tracked
- **Structured Logging**: Consistent log format for monitoring integration
- **Log Rotation**: Automatic log rotation to prevent disk space issues

### Resource Protection
- **Memory Limits**: Configurable memory usage limits
- **Operation Timeouts**: Automatic timeout for long-running operations
- **File Count Limits**: Protection against processing too many files
- **Rate Limiting**: Controlled file operation rates

## Monitoring and Observability

### Health Monitoring
- **System Resources**: CPU, memory, and disk usage monitoring
- **Directory Access**: Target directory accessibility validation
- **Email Connectivity**: SMTP server connectivity checks
- **Application Health**: Overall application health status

### Performance Metrics
- **Operation Metrics**: Count and timing of all operations
- **Error Metrics**: Error rates and types
- **System Metrics**: Resource usage and performance
- **Business Metrics**: Files processed, deleted, and preserved

### Metrics Export
```
# Prometheus format metrics available
GET /metrics

# Health check endpoint
GET /health

# Detailed health information
GET /health/detailed
```

## Production Deployment

### System Requirements
- **Operating System**: Windows 10/Server 2016 or later
- **Memory**: Minimum 512MB, recommended 1GB
- **Disk Space**: 100MB for application, additional space for logs and reports
- **Network**: SMTP access if email notifications enabled

### Installation
1. **Extract**: Extract distribution ZIP to target directory
2. **Configure**: Edit `dirpurge.ini` with your settings
3. **Test**: Run with `--dry-run` to validate configuration
4. **Schedule**: Set up scheduled execution via Task Scheduler

### Monitoring Integration
```python
# Example Prometheus configuration
- job_name: 'dirpurge'
  static_configs:
    - targets: ['localhost:8080']
  metrics_path: '/metrics'
  scrape_interval: 30s
```

### Alerting Rules
```yaml
# Example alert rules
- alert: DirPurgeHighErrorRate
  expr: rate(app_errors_total[5m]) > 0.1
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "DirPurge error rate is high"

- alert: DirPurgeHealthCheckFailed
  expr: up{job="dirpurge"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "DirPurge health check failed"
```

## Building from Source

### Requirements
- Python 3.8+
- Required packages: `pip install -r requirements.txt`
- Build tools: `pip install -r requirements-build.txt`

### Build Process
```cmd
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt

# Run tests
python -m pytest

# Run property-based tests
python -m pytest tests/ -v

# Build executable
python build.py
```

### Development Setup
```cmd
# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt

# Run tests with coverage
python -m pytest --cov=src tests/

# Run security checks
bandit -r src/

# Run code quality checks
flake8 src/
mypy src/
```

## Testing

### Test Coverage
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Property-Based Tests**: Randomized input testing for edge cases
- **Security Tests**: Input validation and security feature testing

### Running Tests
```cmd
# All tests
python -m pytest

# Specific test categories
python -m pytest tests/test_security.py
python -m pytest tests/test_integration.py

# Property-based tests with verbose output
python -m pytest tests/ -v --tb=short
```

## Troubleshooting

### Common Issues

#### Configuration Errors
```
Error: Configuration validation failed
Solution: Check INI file syntax and required fields
```

#### Permission Denied
```
Error: Permission denied accessing directory
Solution: Run with appropriate permissions or check directory access
```

#### SMTP Connection Failed
```
Error: SMTP server not accessible
Solution: Verify server settings and network connectivity
```

### Diagnostic Commands
```cmd
# Test configuration
dirpurge.exe --dry-run --target-directory "C:\test"

# Verbose logging
dirpurge.exe --dry-run --verbose

# Health check
dirpurge.exe --health-check
```

### Log Analysis
```cmd
# View recent logs
type logs\dirpurge.log | findstr ERROR

# Monitor real-time logs
powershell Get-Content logs\dirpurge.log -Wait -Tail 10
```

## Support and Contributing

### Getting Help
- Check the troubleshooting section above
- Review log files in the `logs/` directory
- Verify configuration with `--dry-run` mode
- Check system health with health monitoring

### Reporting Issues
When reporting issues, please include:
- DirPurge version (`dirpurge.exe --version`)
- Configuration file (with sensitive data removed)
- Relevant log entries
- Steps to reproduce the issue

### Development
- Follow the multi-agent development process (see `DEVELOPER_FAQ.md`)
- All changes must include tests and documentation
- Security changes require additional review
- Performance changes should include benchmarks

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### Version 1.3.0 (Current)
- **MAJOR RELEASE**: Complete production-grade transformation
- Added comprehensive security hardening with input validation and threat protection
- Implemented production monitoring and health checks
- Added graceful shutdown and circuit breaker patterns for fault tolerance
- Enhanced architecture with dependency injection and loose coupling
- Added performance metrics collection with Prometheus export
- Implemented resource management with memory limits and timeouts
- Added structured logging with sensitive data filtering
- Created multi-agent development process framework
- Added comprehensive documentation and compliance metrics
- **Breaking Changes**: None - all original functionality preserved
- **New Dependencies**: psutil for system monitoring

### Version 1.2.6
- Added XLSX export functionality for file set summaries
- Enhanced configuration with generic examples
- Improved build process and artifact organization

### Previous Versions
See `releases/` directory for historical versions and detailed changelog.