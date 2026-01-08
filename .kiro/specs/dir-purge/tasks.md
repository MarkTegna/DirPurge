# Implementation Plan: DirPurge

## Overview

This implementation plan breaks down the DirPurge file management utility into discrete coding tasks. Each task builds incrementally toward a complete Windows executable that can purge old files while preserving recent ones based on configurable criteria.

## Tasks

- [x] 1. Set up project structure and core data models
  - Create directory structure with src/, tests/, reports/ folders
  - Define core data classes (FileInfo, Config, EmailConfig, PurgeResult)
  - Set up version management with version.py file
  - Configure testing framework with pytest and hypothesis
  - _Requirements: All requirements (foundational)_

- [x] 1.1 Write property test for data model validation
  - **Property 16: Timestamp Validation**
  - **Validates: Requirements 7.4**

- [x] 2. Implement configuration management system
  - [x] 2.1 Create INI file parser with configparser
    - Implement Config class with default values
    - Add INI file reading and validation
    - _Requirements: 3.1, 7.3_

  - [x] 2.2 Write property test for INI parsing
    - **Property 6: Configuration Parsing**
    - **Validates: Requirements 3.1**

  - [x] 2.3 Implement CLI argument parser with argparse
    - Add all CLI arguments matching INI options
    - Implement help system and validation
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 2.4 Write property test for CLI precedence
    - **Property 5: Configuration Precedence**
    - **Validates: Requirements 3.2, 3.5**

  - [x] 2.5 Write property test for CLI validation
    - **Property 18: CLI Validation**
    - **Validates: Requirements 8.3**

- [x] 3. Implement file scanning and grouping engine
  - [x] 3.1 Create FileScanner class with os.scandir()
    - Implement efficient directory traversal
    - Add file information extraction (size, timestamps)
    - _Requirements: 1.1, 1.2_

  - [x] 3.2 Write property test for file grouping
    - **Property 1: File Grouping Correctness**
    - **Validates: Requirements 1.1, 1.2**

  - [x] 3.3 Add extension filtering functionality
    - Implement configurable extension exclusion
    - Add case-insensitive extension matching
    - _Requirements: 1.3, 1.4_

  - [x] 3.4 Write property test for extension filtering
    - **Property 2: Extension Filtering**
    - **Validates: Requirements 1.3, 1.4**

- [x] 4. Checkpoint - Ensure file scanning tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement purge engine with preservation rules
  - [x] 5.1 Create PurgeEngine class
    - Implement file sorting by modification time
    - Add preservation logic (count and age thresholds)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 5.2 Write property test for file preservation
    - **Property 3: File Preservation Rules**
    - **Validates: Requirements 2.1, 2.2, 2.4**

  - [x] 5.3 Write property test for file ordering
    - **Property 4: File Ordering Consistency**
    - **Validates: Requirements 2.3**

  - [x] 5.4 Add dry run mode implementation
    - Implement safe mode that reports without deleting
    - Add dry run indicators in output
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 5.5 Write property test for dry run safety
    - **Property 8: Dry Run Safety**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [x] 6. Implement reporting system
  - [x] 6.1 Create Reporter class
    - Implement report generation with file counts and statistics
    - Add YYYYMMDD-HH-MM filename formatting
    - Create reports directory if needed
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 6.2 Write property test for report generation
    - **Property 9: Report Generation**
    - **Validates: Requirements 5.1, 5.2**

  - [x] 6.3 Write property test for filename formatting
    - **Property 10: Report Filename Format**
    - **Validates: Requirements 5.3**

- [x] 7. Implement email notification system
  - [x] 7.1 Create EmailService class with smtplib
    - Implement SMTP connection and authentication
    - Add email message creation and sending
    - Include error handling for email failures
    - _Requirements: 5.4, 6.1, 6.2, 6.3, 6.4_

  - [x] 7.2 Write property test for email notifications
    - **Property 11: Email Notification**
    - **Validates: Requirements 5.4, 6.1, 6.4**

  - [x] 7.3 Write property test for SMTP configuration
    - **Property 12: SMTP Configuration**
    - **Validates: Requirements 6.2**

  - [x] 7.4 Write property test for email content
    - **Property 13: Email Content Completeness**
    - **Validates: Requirements 6.3**

- [x] 8. Implement error handling and validation
  - [x] 8.1 Add comprehensive error handling
    - Implement file access error handling
    - Add configuration validation with specific error messages
    - Handle missing directories and permission issues
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 8.2 Write property test for file access errors
    - **Property 14: File Access Error Handling**
    - **Validates: Requirements 7.2**

  - [x] 8.3 Write property test for configuration validation
    - **Property 15: Configuration Validation**
    - **Validates: Requirements 7.3**

- [x] 9. Create main application entry point
  - [x] 9.1 Implement main() function
    - Wire all components together
    - Add command-line interface integration
    - Implement help display for no arguments case
    - _Requirements: 3.3_

  - [x] 9.2 Write property test for INI immutability
    - **Property 7: INI File Immutability**
    - **Validates: Requirements 3.4**

  - [x] 9.3 Write property test for CLI argument coverage
    - **Property 17: CLI Argument Coverage**
    - **Validates: Requirements 8.1**

  - [x] 9.4 Write property test for argument format support
    - **Property 19: Argument Format Support**
    - **Validates: Requirements 8.4**

- [x] 10. Create example configuration and build system
  - [x] 10.1 Create example INI file with all options
    - Include default values and commented optional settings
    - Add email configuration template
    - Use generic examples for production build
    - _Requirements: 3.1, 6.2_

  - [x] 10.2 Implement version management and build scripts
    - Create increment_build.py for automatic version increments
    - Add update_version.py for manual version updates
    - Implement Windows executable packaging
    - _Requirements: Version management standards_

- [x] 11. Final integration and testing
  - [x] 11.1 Create comprehensive integration tests
    - Test end-to-end workflows with temporary directories
    - Verify Windows executable functionality
    - Test with various file set configurations
    - _Requirements: All requirements (integration)_

  - [x] 11.2 Final checkpoint - Ensure all tests pass
    - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Property tests validate universal correctness properties using hypothesis
- Unit tests validate specific examples and edge cases
- Checkpoints ensure incremental validation throughout development
- Version management follows MAJOR.MINOR.PATCH format with automatic PATCH increments