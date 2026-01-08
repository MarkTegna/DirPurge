"""Tests for email service functionality"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from src.email_service import EmailService
from src.models import EmailConfig


class TestEmailService:
    """Test cases for EmailService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.email_config = EmailConfig(
            send_email=True,
            smtp_server="smtp.test.com",
            smtp_port=587,
            smtp_use_tls=True,
            smtp_username="testuser",
            smtp_password="testpass",
            from_email="from@test.com",
            to_email="to@test.com"
        )
        self.email_service = EmailService(self.email_config)
    
    @given(
        report_content=st.text(min_size=10, max_size=200).filter(lambda x: x.isascii()),
        smtp_server=st.sampled_from(["smtp.gmail.com", "smtp.test.com", "mail.example.org"]),
        smtp_port=st.sampled_from([25, 587, 465]),
        from_email=st.sampled_from(["test@example.com", "user@test.org", "admin@company.net"]),
        to_email=st.sampled_from(["recipient@example.com", "user@test.org", "admin@company.net"])
    )
    @settings(max_examples=5)  # Reduced for faster execution
    def test_property_11_email_notification(self, report_content, smtp_server, smtp_port, from_email, to_email):
        """
        Property 11: Email Notification
        For any purge operation when email is enabled, reports should be sent via SMTP with proper error handling.
        **Feature: dir-purge, Property 11: Email Notification**
        **Validates: Requirements 5.4, 6.1, 6.4**
        """
        # Create email config with generated values
        email_config = EmailConfig(
            send_email=True,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_use_tls=False,
            smtp_username="user",
            smtp_password="pass",
            from_email=from_email,
            to_email=to_email
        )
        
        email_service = EmailService(email_config)
        
        # Mock SMTP to avoid actual email sending
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # Test successful email sending
            result = email_service.send_report(report_content)
            
            # Verify email was attempted to be sent
            assert result == True
            mock_smtp.assert_called_once_with(smtp_server, smtp_port)
            mock_server.login.assert_called_once_with("user", "pass")
            mock_server.send_message.assert_called_once()
            
            # Verify message content
            sent_message = mock_server.send_message.call_args[0][0]
            assert sent_message['From'] == from_email
            assert sent_message['To'] == to_email
            assert 'DirPurge Report' in sent_message['Subject']
    
    def test_email_disabled(self):
        """Test behavior when email is disabled"""
        config = EmailConfig(send_email=False)
        service = EmailService(config)
        
        result = service.send_report("test content")
        assert result == True  # Should succeed when disabled
    
    def test_invalid_config(self):
        """Test behavior with invalid email configuration"""
        config = EmailConfig(
            send_email=True,
            smtp_server="",  # Invalid: empty server
            from_email="test@test.com",
            to_email="test@test.com"
        )
        service = EmailService(config)
        
        result = service.send_report("test content")
        assert result == False  # Should fail with invalid config
    
    def test_smtp_connection_error(self):
        """Test error handling for SMTP connection failures"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("Connection failed")
            
            result = self.email_service.send_report("test content")
            assert result == False  # Should handle error gracefully
    
    def test_message_creation(self):
        """Test email message creation"""
        report_content = "Test report content"
        custom_subject = "Custom Subject"
        
        message = self.email_service._create_message(report_content, custom_subject)
        
        assert message['From'] == self.email_config.from_email
        assert message['To'] == self.email_config.to_email
        assert message['Subject'] == custom_subject
        
        # Verify content is attached
        payload = message.get_payload()
        assert len(payload) == 1
        assert payload[0].get_payload() == report_content
    
    @given(
        smtp_server=st.sampled_from(["smtp.gmail.com", "smtp.test.com", "mail.example.org"]),
        smtp_port=st.sampled_from([25, 587, 465, 993, 995]),
        use_tls=st.booleans(),
        username=st.text(min_size=3, max_size=20).filter(lambda x: x.isalnum()),
        password=st.text(min_size=3, max_size=20).filter(lambda x: x.isalnum())
    )
    @settings(max_examples=5)  # Reduced for faster execution
    def test_property_12_smtp_configuration(self, smtp_server, smtp_port, use_tls, username, password):
        """
        Property 12: SMTP Configuration
        For any valid SMTP configuration, the system should successfully establish connections 
        using the provided server, port, and authentication settings.
        **Feature: dir-purge, Property 12: SMTP Configuration**
        **Validates: Requirements 6.2**
        """
        email_config = EmailConfig(
            send_email=True,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            smtp_use_tls=use_tls,
            smtp_username=username,
            smtp_password=password,
            from_email="test@example.com",
            to_email="recipient@example.com"
        )
        
        email_service = EmailService(email_config)
        
        # Mock SMTP to test configuration handling
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # Test SMTP connection creation
            result = email_service.send_report("test content")
            
            # Verify SMTP was called with correct parameters
            mock_smtp.assert_called_once_with(smtp_server, smtp_port)
            
            # Verify TLS handling
            if use_tls:
                mock_server.starttls.assert_called_once()
            
            # Verify authentication
            mock_server.login.assert_called_once_with(username, password)
            
            # Should succeed with valid config
            assert result == True
    
    @given(
        report_content=st.sampled_from([
            "DirPurge Report: 10 files scanned, 5 deleted, 5 preserved",
            "Summary: No files to delete, all files preserved",
            "Operation completed successfully with 3 errors"
        ]),
        subject_prefix=st.sampled_from(["Daily", "Weekly", "Monthly", "Test", "Production"])
    )
    @settings(max_examples=3)  # Reduced for faster execution
    def test_property_13_email_content_completeness(self, report_content, subject_prefix):
        """
        Property 13: Email Content Completeness
        For any email report, the message should include purge summary and statistics.
        **Feature: dir-purge, Property 13: Email Content Completeness**
        **Validates: Requirements 6.3**
        """
        custom_subject = f"{subject_prefix} Report"
        
        # Create email message
        message = self.email_service._create_message(report_content, custom_subject)
        
        # Verify message structure
        assert message['From'] == self.email_config.from_email
        assert message['To'] == self.email_config.to_email
        assert message['Subject'] == custom_subject
        
        # Verify content completeness
        payload = message.get_payload()
        assert len(payload) == 1
        
        email_body = payload[0].get_payload()
        assert email_body == report_content
        
        # Verify content type
        assert payload[0].get_content_type() == 'text/plain'
        
        # Test with default subject
        default_message = self.email_service._create_message(report_content)
        assert 'DirPurge Report' in default_message['Subject']