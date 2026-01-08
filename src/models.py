"""Core data models for DirPurge"""

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import List, Optional


@dataclass
class FileInfo:
    """Information about a file to be processed"""
    path: Path
    name: str
    prefix: str  # Part before "__"
    size: int
    modified_time: datetime
    extension: str


@dataclass
class EmailConfig:
    """Email configuration settings"""
    send_email: bool = False
    smtp_server: str = ''
    smtp_port: int = 25
    smtp_use_tls: bool = False
    smtp_username: str = ''
    smtp_password: str = ''
    from_email: str = ''
    to_email: str = ''


@dataclass
class Config:
    """Main configuration for DirPurge"""
    target_directory: str
    min_files_to_keep: int = 50
    max_age_days: int = 366
    excluded_extensions: List[str] = field(default_factory=lambda: ['.PL', '.TXT', '.CSV', '.ZIP'])
    dry_run: bool = False
    reports_directory: str = './reports'
    email_settings: Optional[EmailConfig] = None


@dataclass
class PurgeResult:
    """Results of a purge operation"""
    total_files_scanned: int
    file_sets_found: int
    files_to_delete: List[FileInfo]
    files_preserved: List[FileInfo]
    actual_deletions: int
    errors: List[str]
    execution_time: float