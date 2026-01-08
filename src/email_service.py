"""Email notification service for DirPurge"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from .models import EmailConfig


class EmailService:
    """Sends email notifications using SMTP"""
    
    def __init__(self, email_config: EmailConfig):
        """Initialize email service with configuration"""
        self.config = email_config
    
    def send_report(self, report_content: str, subject: str = None) -> bool:
        """Send report via email"""
        if not self.config.send_email:
            return True  # Email disabled, consider success
        
        if not self._validate_config():
            print("Warning: Email configuration is invalid, skipping email notification")
            return False
        
        try:
            # Create message
            message = self._create_message(report_content, subject)
            
            # Send email
            with self._connect_smtp() as server:
                if self.config.smtp_username and self.config.smtp_password:
                    server.login(self.config.smtp_username, self.config.smtp_password)
                
                server.send_message(message)
            
            print(f"Email report sent successfully to {self.config.to_email}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to send email: {e}"
            print(f"Warning: {error_msg}")
            return False
    
    def _validate_config(self) -> bool:
        """Validate email configuration"""
        if not self.config.smtp_server:
            return False
        if not self.config.from_email:
            return False
        if not self.config.to_email:
            return False
        if self.config.smtp_port <= 0 or self.config.smtp_port > 65535:
            return False
        return True
    
    def _create_message(self, report_content: str, subject: str = None) -> MIMEMultipart:
        """Create email message with report content"""
        if subject is None:
            subject = f"DirPurge Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        message = MIMEMultipart()
        message['From'] = self.config.from_email
        message['To'] = self.config.to_email
        message['Subject'] = subject
        
        # Add report content as plain text
        body = MIMEText(report_content, 'plain')
        message.attach(body)
        
        return message
    
    def _connect_smtp(self) -> smtplib.SMTP:
        """Create SMTP connection"""
        if self.config.smtp_use_tls:
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
        
        return server