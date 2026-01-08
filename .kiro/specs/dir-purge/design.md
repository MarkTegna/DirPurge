# Design Document: DirPurge

## Overview

DirPurge is a Windows-based file management utility written in Python that automatically purges old files from target directories while preserving recent files and maintaining minimum counts per file set. The application uses a modular architecture with clear separation between configuration management, file operations, reporting, and email notifications.

## Architecture

The system follows a layered architecture pattern:

```
┌─────────────────────────────────────────┐
│              CLI Interface              │
├─────────────────────────────────────────┤
│           Configuration Layer           │
├─────────────────────────────────────────┤
│            Business Logic               │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │ File Scanner│  │ Purge Engine    │   │
│  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────┤
│              Services Layer             │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │   Reporter  │  │ Email Service   │   │
│  └─────────────┘  └─────────────────┘   │
├─────────────────────────────────────────┤
│            Infrastructure               │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │File System │  │   SMTP Client   │   │
│  └─────────────┘  └─────────────────┘   │
└─────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Configuration Manager
**Purpose**: Handles INI file parsing and CLI argument processing with proper precedence.

**Key Methods**:
- `load_config(ini_path: str) -> ConfigDict`
- `parse_cli_args(args: List[str]) -> ConfigDict`
- `merge_configs(ini_config: ConfigDict, cli_config: ConfigDict) -> ConfigDict`

**Dependencies**: Uses Python's `configparser` and `argparse` modules.

### 2. File Scanner
**Purpose**: Efficiently scans target directory and groups files by prefix.

**Key Methods**:
- `scan_directory(path: str) -> Dict[str, List[FileInfo]]`
- `group_files_by_prefix(files: List[FileInfo]) -> Dict[str, List[FileInfo]]`
- `filter_by_extensions(files: List[FileInfo], excluded_exts: List[str]) -> List[FileInfo]`

**Implementation Notes**:
- Uses `os.scandir()` for efficient directory traversal ([source](https://zetcode.com/python/os-scandir/))
- Leverages `DirEntry` objects for fast file stat operations
- Handles Windows-specific path separators using `pathlib`

### 3. Purge Engine
**Purpose**: Determines which files to delete based on age and count criteria.

**Key Methods**:
- `determine_files_to_purge(file_groups: Dict[str, List[FileInfo]], config: Config) -> List[FileInfo]`
- `apply_preservation_rules(files: List[FileInfo], min_count: int, max_age_days: int) -> List[FileInfo]`
- `execute_purge(files_to_delete: List[FileInfo], dry_run: bool) -> PurgeResult`

**Business Rules**:
- Sort files by modification time (newest first)
- Preserve minimum count (default: 50 files per set)
- Preserve files newer than threshold (default: 366 days)
- Only delete files that exceed both criteria

### 4. Reporter
**Purpose**: Generates detailed reports of purge operations.

**Key Methods**:
- `generate_report(purge_result: PurgeResult, config: Config) -> Report`
- `save_report(report: Report, output_path: str) -> None`
- `format_filename(timestamp: datetime) -> str`  # Uses YYYYMMDD-HH-MM format

### 5. Email Service
**Purpose**: Sends email notifications using SMTP.

**Key Methods**:
- `send_report(report: Report, email_config: EmailConfig) -> bool`
- `create_message(report: Report, from_addr: str, to_addr: str) -> MIMEText`
- `connect_smtp(server: str, port: int, use_tls: bool) -> SMTPConnection`

**Implementation Notes**:
- Uses Python's `smtplib` for SMTP operations ([source](https://docs.python.org/3/library/smtplib.html))
- Supports both authenticated and unauthenticated SMTP
- Graceful error handling for email failures

## Data Models

### FileInfo
```python
@dataclass
class FileInfo:
    path: Path
    name: str
    prefix: str  # Part before "__"
    size: int
    modified_time: datetime
    extension: str
```

### Config
```python
@dataclass
class Config:
    target_directory: str
    min_files_to_keep: int = 50
    max_age_days: int = 366
    excluded_extensions: List[str] = field(default_factory=lambda: ['.PL', '.TXT', '.CSV', '.ZIP'])
    dry_run: bool = False
    reports_directory: str = './reports'
    email_settings: Optional[EmailConfig] = None
```

### EmailConfig
```python
@dataclass
class EmailConfig:
    send_email: bool = False
    smtp_server: str = ''
    smtp_port: int = 25
    smtp_use_tls: bool = False
    smtp_username: str = ''
    smtp_password: str = ''
    from_email: str = ''
    to_email: str = ''
```

### PurgeResult
```python
@dataclass
class PurgeResult:
    total_files_scanned: int
    file_sets_found: int
    files_to_delete: List[FileInfo]
    files_preserved: List[FileInfo]
    actual_deletions: int
    errors: List[str]
    execution_time: float
```

Now I need to use the prework tool to analyze the acceptance criteria before writing the correctness properties:
## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: File Grouping Correctness
*For any* directory containing files, files with "__" delimiter should be grouped by their prefix, and files without "__" should be ignored entirely.
**Validates: Requirements 1.1, 1.2**

### Property 2: Extension Filtering
*For any* configured exclusion list and file collection, all files with excluded extensions should be filtered out before processing.
**Validates: Requirements 1.3, 1.4**

### Property 3: File Preservation Rules
*For any* file set, the system should preserve the newest N files and all files younger than the age threshold, where N is the minimum count setting.
**Validates: Requirements 2.1, 2.2, 2.4**

### Property 4: File Ordering Consistency
*For any* collection of files with timestamps, the system should consistently order them by modification time with newest first.
**Validates: Requirements 2.3**

### Property 5: Configuration Precedence
*For any* combination of INI file settings and CLI arguments, CLI arguments should always override corresponding INI values.
**Validates: Requirements 3.2, 3.5**

### Property 6: Configuration Parsing
*For any* valid INI file content, the system should correctly parse all configuration sections and values.
**Validates: Requirements 3.1**

### Property 7: INI File Immutability
*For any* CLI operation, the original INI file content should remain unchanged after program execution.
**Validates: Requirements 3.4**

### Property 8: Dry Run Safety
*For any* purge operation in dry run mode, no files should be deleted and all reporting should function normally.
**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 9: Report Generation
*For any* purge operation, generated reports should contain file counts, deletion counts, timestamps, and be saved in the configured reports directory.
**Validates: Requirements 5.1, 5.2**

### Property 10: Report Filename Format
*For any* report generation timestamp, the filename should follow YYYYMMDD-HH-MM format exactly.
**Validates: Requirements 5.3**

### Property 11: Email Notification
*For any* purge operation when email is enabled, reports should be sent via SMTP with proper error handling.
**Validates: Requirements 5.4, 6.1, 6.4**

### Property 12: SMTP Configuration
*For any* valid SMTP configuration, the system should successfully establish connections using the provided server, port, and authentication settings.
**Validates: Requirements 6.2**

### Property 13: Email Content Completeness
*For any* email report, the message should include purge summary and statistics.
**Validates: Requirements 6.3**

### Property 14: File Access Error Handling
*For any* file access error during processing, the system should log the error and continue processing remaining files.
**Validates: Requirements 7.2**

### Property 15: Configuration Validation
*For any* invalid configuration input, the system should provide specific validation error messages.
**Validates: Requirements 7.3**

### Property 16: Timestamp Validation
*For any* file with invalid or missing timestamps, the system should handle the error gracefully without crashing.
**Validates: Requirements 7.4**

### Property 17: CLI Argument Coverage
*For any* configuration option available in INI files, there should be a corresponding CLI argument.
**Validates: Requirements 8.1**

### Property 18: CLI Validation
*For any* invalid CLI argument value, the system should report specific validation errors.
**Validates: Requirements 8.3**

### Property 19: Argument Format Support
*For any* CLI argument that supports both formats, both short and long forms should work identically.
**Validates: Requirements 8.4**

## Error Handling

### File System Errors
- **Missing Target Directory**: Validate directory existence before processing, exit with clear error message
- **Permission Denied**: Log individual file access errors, continue with remaining files
- **Disk Space Issues**: Monitor available space during operations, fail gracefully if insufficient

### Configuration Errors
- **Missing INI File**: Display help and exit when no configuration source is available
- **Invalid INI Format**: Provide specific parsing error messages with line numbers
- **Invalid CLI Arguments**: Use argparse validation with descriptive error messages

### Network Errors (Email)
- **SMTP Connection Failures**: Log error, continue operation without email notification
- **Authentication Failures**: Provide clear error messages for credential issues
- **Message Sending Failures**: Retry once, then log failure and continue

### Data Integrity
- **Timestamp Parsing**: Handle invalid file timestamps by using file creation time as fallback
- **Path Resolution**: Validate and normalize all file paths before operations
- **Concurrent Access**: Handle files being modified during scanning operations

## Testing Strategy

### Unit Testing Approach
The system will use a dual testing approach combining unit tests for specific scenarios and property-based tests for comprehensive validation:

**Unit Tests Focus Areas**:
- Configuration parsing edge cases (empty files, malformed INI)
- Email sending with various SMTP configurations
- Error handling scenarios (missing directories, permission denied)
- Report generation with specific data sets
- CLI argument parsing with invalid inputs

**Property-Based Testing Framework**:
The system will use Python's `hypothesis` library for property-based testing. Each correctness property will be implemented as a property-based test with minimum 100 iterations per test.

**Property Test Configuration**:
- **Test Framework**: Python `hypothesis` library
- **Iterations**: Minimum 100 per property test
- **Test Tagging**: Each test tagged with format: **Feature: dir-purge, Property {number}: {property_text}**
- **Data Generators**: Custom generators for file structures, timestamps, and configurations

**Integration Testing**:
- End-to-end testing with temporary directories and mock SMTP servers
- Cross-platform path handling validation
- Performance testing with large file sets (1000+ files)

**Test Data Management**:
- Temporary directory creation for isolated test environments
- Mock file systems for testing without actual file operations
- Configurable test data generators for various file set scenarios

The testing strategy ensures both concrete examples work correctly (unit tests) and universal properties hold across all possible inputs (property tests), providing comprehensive validation of system correctness.