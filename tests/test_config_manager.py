"""Tests for configuration management"""

import pytest
import tempfile
import os
from pathlib import Path
from hypothesis import given, strategies as st
from src.config_manager import ConfigManager
from src.models import EmailConfig


class TestConfigManager:
    """Test cases for ConfigManager"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config_manager = ConfigManager()
    
    @given(
        target_dir=st.text(min_size=1, max_size=50).filter(lambda x: not any(c in x for c in '<>:"|?*\n\r') and x.isascii()),
        min_files=st.integers(min_value=0, max_value=1000),
        max_age=st.integers(min_value=0, max_value=3650),
        dry_run=st.booleans(),
        reports_dir=st.text(min_size=1, max_size=50).filter(lambda x: not any(c in x for c in '<>:"|?*\n\r') and x.isascii()),
        send_email=st.booleans(),
        smtp_server=st.text(min_size=0, max_size=100).filter(lambda x: x.isascii()),
        smtp_port=st.integers(min_value=1, max_value=65535),
        smtp_use_tls=st.booleans(),
        from_email=st.text(min_size=0, max_size=100).filter(lambda x: x.isascii()),
        to_email=st.text(min_size=0, max_size=100).filter(lambda x: x.isascii())
    )
    def test_property_6_configuration_parsing(self, target_dir, min_files, max_age, dry_run, 
                                            reports_dir, send_email, smtp_server, smtp_port, 
                                            smtp_use_tls, from_email, to_email):
        """
        Property 6: Configuration Parsing
        For any valid INI file content, the system should correctly parse all configuration sections and values.
        **Feature: dir-purge, Property 6: Configuration Parsing**
        **Validates: Requirements 3.1**
        """
        # Create a temporary INI file with generated content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as f:
            f.write(f"""[general]
target_directory = {target_dir}
min_files_to_keep = {min_files}
max_age_days = {max_age}
excluded_extensions = .PL,.TXT,.CSV,.ZIP
dry_run = {str(dry_run).lower()}
reports_directory = {reports_dir}

[email]
send_email = {str(send_email).lower()}
smtp_server = {smtp_server}
smtp_port = {smtp_port}
smtp_use_tls = {str(smtp_use_tls).lower()}
smtp_username = testuser
smtp_password = testpass
from_email = {from_email}
to_email = {to_email}
""")
            ini_path = f.name
        
        try:
            # Parse the INI file
            config_dict = self.config_manager.load_config_from_ini(ini_path)
            
            # Verify all values were parsed correctly
            assert config_dict['target_directory'] == target_dir
            assert config_dict['min_files_to_keep'] == min_files
            assert config_dict['max_age_days'] == max_age
            assert config_dict['excluded_extensions'] == ['.PL', '.TXT', '.CSV', '.ZIP']
            assert config_dict['dry_run'] == dry_run
            assert config_dict['reports_directory'] == reports_dir
            
            # Verify email configuration
            email_config = config_dict['email_settings']
            assert isinstance(email_config, EmailConfig)
            assert email_config.send_email == send_email
            assert email_config.smtp_server == smtp_server
            assert email_config.smtp_port == smtp_port
            assert email_config.smtp_use_tls == smtp_use_tls
            assert email_config.smtp_username == 'testuser'
            assert email_config.smtp_password == 'testpass'
            assert email_config.from_email == from_email
            assert email_config.to_email == to_email
            
        finally:
            # Clean up temporary file
            os.unlink(ini_path)
    
    @given(
        ini_target_dir=st.text(min_size=1, max_size=30).filter(lambda x: not any(c in x for c in '<>:"|?*\n\r')),
        ini_min_files=st.integers(min_value=0, max_value=500),
        ini_max_age=st.integers(min_value=0, max_value=1000),
        cli_target_dir=st.text(min_size=1, max_size=30).filter(lambda x: not any(c in x for c in '<>:"|?*\n\r')),
        cli_min_files=st.integers(min_value=0, max_value=500),
        cli_max_age=st.integers(min_value=0, max_value=1000),
        cli_dry_run=st.booleans()
    )
    def test_property_5_configuration_precedence(self, ini_target_dir, ini_min_files, ini_max_age,
                                                cli_target_dir, cli_min_files, cli_max_age, cli_dry_run):
        """
        Property 5: Configuration Precedence
        For any combination of INI file settings and CLI arguments, CLI arguments should always override corresponding INI values.
        **Feature: dir-purge, Property 5: Configuration Precedence**
        **Validates: Requirements 3.2, 3.5**
        """
        # Create INI config
        ini_config = {
            'target_directory': ini_target_dir,
            'min_files_to_keep': ini_min_files,
            'max_age_days': ini_max_age,
            'dry_run': False,
            'email_settings': EmailConfig(send_email=False, smtp_server='ini_server')
        }
        
        # Create CLI config with different values
        cli_config = {
            'target_directory': cli_target_dir,
            'min_files_to_keep': cli_min_files,
            'max_age_days': cli_max_age,
            'dry_run': cli_dry_run,
            'email_settings': EmailConfig(send_email=True, smtp_server='cli_server')
        }
        
        # Merge configurations
        merged = self.config_manager.merge_configs(ini_config, cli_config)
        
        # CLI values should override INI values
        assert merged['target_directory'] == cli_target_dir
        assert merged['min_files_to_keep'] == cli_min_files
        assert merged['max_age_days'] == cli_max_age
        assert merged['dry_run'] == cli_dry_run
        
        # Email settings should be merged with CLI taking precedence
        assert merged['email_settings'].send_email == True  # CLI value
        assert merged['email_settings'].smtp_server == 'cli_server'  # CLI value
    
    def test_missing_ini_file(self):
        """Test behavior when INI file doesn't exist"""
        config_dict = self.config_manager.load_config_from_ini('nonexistent.ini')
        assert config_dict == {}
    
    def test_empty_ini_file(self):
        """Test behavior with empty INI file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("")
            ini_path = f.name
        
        try:
            config_dict = self.config_manager.load_config_from_ini(ini_path)
            assert config_dict['email_settings'] is None
        finally:
            os.unlink(ini_path)
    
    def test_malformed_ini_file(self):
        """Test error handling for malformed INI files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("[general\ntarget_directory = test")  # Missing closing bracket
            ini_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Invalid INI file format"):
                self.config_manager.load_config_from_ini(ini_path)
        finally:
            os.unlink(ini_path)
    
    def test_extension_parsing(self):
        """Test extension parsing functionality"""
        # Test normal case
        extensions = self.config_manager._parse_extensions(".py,.txt,.csv")
        assert extensions == ['.PY', '.TXT', '.CSV']
        
        # Test empty string
        extensions = self.config_manager._parse_extensions("")
        assert extensions == []
        
        # Test whitespace handling
        extensions = self.config_manager._parse_extensions(" .py , .txt , .csv ")
        assert extensions == ['.PY', '.TXT', '.CSV']
    
    @given(
        min_files=st.integers().filter(lambda x: x < 0),
        max_age=st.integers().filter(lambda x: x < 0),
        smtp_port=st.integers().filter(lambda x: x <= 0 or x > 65535)
    )
    def test_property_18_cli_validation(self, min_files, max_age, smtp_port):
        """
        Property 18: CLI Validation
        For any invalid CLI argument value, the system should report specific validation errors.
        **Feature: dir-purge, Property 18: CLI Validation**
        **Validates: Requirements 8.3**
        """
        # Test invalid min_files
        config_dict = {'min_files_to_keep': min_files}
        with pytest.raises(ValueError, match="--min-files must be non-negative"):
            self.config_manager.validate_cli_args(config_dict)
        
        # Test invalid max_age
        config_dict = {'max_age_days': max_age}
        with pytest.raises(ValueError, match="--max-age must be non-negative"):
            self.config_manager.validate_cli_args(config_dict)
        
        # Test invalid smtp_port
        from src.models import EmailConfig
        email_config = EmailConfig(smtp_port=smtp_port)
        config_dict = {'email_settings': email_config}
        with pytest.raises(ValueError, match="--smtp-port must be between 1 and 65535"):
            self.config_manager.validate_cli_args(config_dict)
    
    def test_cli_argument_parsing(self):
        """Test CLI argument parsing functionality"""
        # Test basic arguments
        args = ['--target-directory', '/test', '--min-files', '100', '--dry-run']
        config_dict = self.config_manager.parse_cli_args(args)
        
        assert config_dict['target_directory'] == '/test'
        assert config_dict['min_files_to_keep'] == 100
        assert config_dict['dry_run'] == True
        
        # Test email arguments
        args = ['--send-email', '--smtp-server', 'smtp.test.com', '--smtp-port', '587']
        config_dict = self.config_manager.parse_cli_args(args)
        
        email_config = config_dict['email_settings']
        assert email_config.send_email == True
        assert email_config.smtp_server == 'smtp.test.com'
        assert email_config.smtp_port == 587