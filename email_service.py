"""
Email notification service for Guide platform
Handles transactional emails for welcomes, subscription renewals, and support
"""

import os
import logging
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending transactional emails"""
    
    def __init__(self):
        # Try to use SendGrid API key (from Replit integration)
        self.sendgrid_key = os.getenv("SENDGRID_API_KEY")
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", "support@auxpery.com.au")
        self.from_name = "Guide - Montessori Curriculum"
        
    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Send an email using available service
        Falls back gracefully if email is not configured
        """
        try:
            if self.sendgrid_key:
                return self._send_via_sendgrid(to_email, subject, html_content)
            elif self.smtp_user and self.smtp_password:
                return self._send_via_smtp(to_email, subject, html_content)
            else:
                logger.warning("Email service not configured - skipping email")
                return False
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    def _send_via_sendgrid(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email via SendGrid API"""
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            sg = sendgrid.SendGridAPIClient(self.sendgrid_key)
            response = sg.send(message)
            
            logger.info(f"Email sent to {to_email} via SendGrid (status: {response.status_code})")
            return response.status_code in [200, 201, 202]
        except Exception as e:
            logger.error(f"SendGrid error: {str(e)}")
            return False
    
    def _send_via_smtp(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email via SMTP (Gmail, etc.)"""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Attach HTML content
            part = MIMEText(html_content, "html")
            message.attach(part)
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Email sent to {to_email} via SMTP")
            return True
        except Exception as e:
            logger.error(f"SMTP error: {str(e)}")
            return False
    
    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email to new educator"""
        html_content = f"""
        <html>
            <body style="font-family: Inter, sans-serif; line-height: 1.6; color: #333333;">
                <div style="max-width: 600px; margin: 0 auto; background: #FFFEFA; padding: 24px; border-radius: 8px;">
                    <h1 style="color: #333333; margin-bottom: 16px;">Welcome to Guide, {user_name}!</h1>
                    
                    <p>We're delighted to have you join our community of educators committed to nurturing the whole child.</p>
                    
                    <p><strong>Getting Started:</strong></p>
                    <ul>
                        <li>Take the guided tour on your first login</li>
                        <li>Explore our Montessori Companion for methodology support</li>
                        <li>Try Lesson Planning with your first class or year level</li>
                        <li>Create student accounts to give them access to the Research Assistant</li>
                    </ul>
                    
                    <p><strong>Need Help?</strong></p>
                    <p>Visit the Support section in your dashboard for resources, or send us feedback directly in the app.</p>
                    
                    <p style="margin-top: 32px; padding-top: 16px; border-top: 1px solid #E6E6E6; font-size: 12px; color: #666666;">
                        Guide is a Montessori curriculum companion designed to help you create interconnected learning experiences.<br>
                        Learn more at <a href="https://auxpery.com.au">auxpery.com.au</a>
                    </p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(user_email, "Welcome to Guide", html_content)
    
    def send_subscription_renewal_reminder(self, user_email: str, user_name: str, 
                                          renewal_date: datetime, plan: str) -> bool:
        """Send subscription renewal reminder email"""
        renewal_str = renewal_date.strftime("%B %d, %Y") if renewal_date else "soon"
        plan_display = "Monthly" if plan == "monthly" else "Yearly"
        
        html_content = f"""
        <html>
            <body style="font-family: Inter, sans-serif; line-height: 1.6; color: #333333;">
                <div style="max-width: 600px; margin: 0 auto; background: #FFFEFA; padding: 24px; border-radius: 8px;">
                    <h1 style="color: #333333; margin-bottom: 16px;">Subscription Renewal Notice</h1>
                    
                    <p>Hello {user_name},</p>
                    
                    <p>This is a friendly reminder that your Guide subscription is renewing on <strong>{renewal_str}</strong>.</p>
                    
                    <p><strong>Your Plan:</strong> {plan_display} subscription to Guide Pro</p>
                    
                    <p><strong>What happens next:</strong></p>
                    <ul>
                        <li>Your subscription will automatically renew on the date shown above</li>
                        <li>Your access to all features continues without interruption</li>
                        <li>You'll receive a receipt after the renewal</li>
                    </ul>
                    
                    <p><strong>Want to change your plan or cancel?</strong></p>
                    <p>Visit the Support section in your Guide dashboard to manage your subscription.</p>
                    
                    <p style="margin-top: 32px; padding-top: 16px; border-top: 1px solid #E6E6E6; font-size: 12px; color: #666666;">
                        Questions? Reply to this email or contact support@auxpery.com.au
                    </p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(user_email, "Your Guide Subscription is Renewing", html_content)
    
    def send_subscription_confirmation(self, user_email: str, user_name: str, 
                                      plan: str, amount: float) -> bool:
        """Send subscription confirmation email after purchase"""
        plan_display = "Monthly" if plan == "monthly" else "Yearly"
        
        html_content = f"""
        <html>
            <body style="font-family: Inter, sans-serif; line-height: 1.6; color: #333333;">
                <div style="max-width: 600px; margin: 0 auto; background: #FFFEFA; padding: 24px; border-radius: 8px;">
                    <h1 style="color: #333333; margin-bottom: 16px;">Subscription Confirmed</h1>
                    
                    <p>Thank you for subscribing to Guide, {user_name}!</p>
                    
                    <p><strong>Subscription Details:</strong></p>
                    <ul>
                        <li>Plan: {plan_display}</li>
                        <li>Amount: ${amount:.2f}</li>
                        <li>Status: Active</li>
                    </ul>
                    
                    <p>Your Guide Pro account is now active. You have full access to all premium features including:</p>
                    <ul>
                        <li>Unlimited Lesson Planning</li>
                        <li>Student Management</li>
                        <li>Advanced AI Coaching</li>
                        <li>Document Analysis</li>
                    </ul>
                    
                    <p style="margin-top: 32px; padding-top: 16px; border-top: 1px solid #E6E6E6; font-size: 12px; color: #666666;">
                        Your receipt has been sent to this email. For questions, visit support@auxpery.com.au
                    </p>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(user_email, "Guide Subscription Confirmed", html_content)


# Singleton instance
_email_service = None

def get_email_service() -> EmailService:
    """Get or create email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
