# Requirements Document

## Introduction

DirPurge is a Windows file management utility that automatically purges old files from a target directory while preserving recent files and maintaining a minimum count per file set. Files are grouped by prefix (part before "__" delimiter) and purged based on age and count thresholds.

## Glossary

- **File_Set**: A group of files sharing the same prefix (part before "__" delimiter)
- **Target_Directory**: The directory where file purging operations are performed
- **Dry_Run_Mode**: A mode where the system reports what would be deleted without actually deleting files
- **Purge_Operation**: The process of deleting files based on age and count criteria
- **Configuration_File**: An INI file containing default settings for the application
- **Report_File**: A log file documenting purge operations and results

## Requirements

### Requirement 1: File Set Identification

**User Story:** As a system administrator, I want files to be grouped by prefix, so that related files are managed together.

#### Acceptance Criteria

1. WHEN processing files, THE System SHALL group files by the prefix before "__" delimiter
2. WHEN a filename does not contain "__", THE System SHALL ignore the file
3. WHEN grouping files, THE System SHALL exclude files with .PL, .TXT, .CSV, and .ZIP extensions by default
4. WHERE extension exclusion is configured, THE System SHALL respect the configured exclusion list

### Requirement 2: File Preservation Rules

**User Story:** As a system administrator, I want to preserve recent and minimum count files, so that important data is not lost.

#### Acceptance Criteria

1. THE System SHALL preserve the last 50 files in each file set by default
2. THE System SHALL preserve any files less than 366 days old by default
3. WHEN determining files to preserve, THE System SHALL order files by date/time with newest first
4. WHEN purging files, THE System SHALL only delete the oldest files that exceed preservation criteria

### Requirement 3: Configuration Management

**User Story:** As a system administrator, I want configurable settings, so that I can customize the purge behavior for different environments.

#### Acceptance Criteria

1. THE System SHALL read configuration from an INI file
2. THE System SHALL support CLI arguments that override INI file settings
3. WHEN no INI file exists and no CLI options are provided, THE System SHALL display help and exit
4. THE System SHALL NOT update the INI file with CLI-provided values
5. THE System SHALL use CLI values over INI values when both are present

### Requirement 4: Dry Run Capability

**User Story:** As a system administrator, I want to preview purge operations, so that I can verify the impact before making changes.

#### Acceptance Criteria

1. WHEN dry run mode is enabled, THE System SHALL report file counts without deleting files
2. WHEN in dry run mode, THE System SHALL show how many files exist in each set
3. WHEN in dry run mode, THE System SHALL show how many files would be deleted
4. THE System SHALL clearly indicate when operating in dry run mode

### Requirement 5: Reporting and Logging

**User Story:** As a system administrator, I want detailed reports of purge operations, so that I can track what was deleted and when.

#### Acceptance Criteria

1. THE System SHALL generate reports in the ./reports directory by default
2. THE System SHALL include file counts, deletion counts, and timestamps in reports
3. THE System SHALL use YYYYMMDD-HH-MM format for report filenames
4. WHERE email is configured, THE System SHALL send reports via email

### Requirement 6: Email Notification

**User Story:** As a system administrator, I want email notifications of purge operations, so that I can monitor the system remotely.

#### Acceptance Criteria

1. WHEN email is enabled in configuration, THE System SHALL send reports via SMTP
2. THE System SHALL support configurable SMTP server, port, and authentication settings
3. THE System SHALL include purge summary and statistics in email reports
4. WHEN email sending fails, THE System SHALL continue operation and log the error

### Requirement 7: Error Handling and Validation

**User Story:** As a system administrator, I want robust error handling, so that the system operates reliably.

#### Acceptance Criteria

1. WHEN the target directory does not exist, THE System SHALL report an error and exit
2. WHEN file access is denied, THE System SHALL log the error and continue with other files
3. WHEN configuration is invalid, THE System SHALL report specific validation errors
4. THE System SHALL validate all date/time operations and handle invalid file timestamps

### Requirement 8: Command Line Interface

**User Story:** As a system administrator, I want comprehensive CLI options, so that I can override any configuration setting.

#### Acceptance Criteria

1. THE System SHALL support CLI arguments for all configurable options
2. THE System SHALL provide help documentation via --help argument
3. THE System SHALL validate CLI arguments and report errors for invalid values
4. THE System SHALL support both short and long argument formats where appropriate