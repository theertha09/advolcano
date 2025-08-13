import logging
from datetime import datetime
import pytz
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
import html
import re

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

# Set up logging
logger = logging.getLogger(__name__)

# Email Configuration - Use environment variables in production
SENDGRID_API_KEY = getattr(settings, 'SENDGRID_API_KEY', None)
ADMIN_EMAIL = getattr(settings, 'ADMIN_EMAIL', 'admin@advolcano.io')
VERIFIED_SENDER_EMAIL = getattr(settings, 'VERIFIED_SENDER_EMAIL', 'noreply@advolcano.io')
MAX_EMAIL_WORKERS = getattr(settings, 'MAX_EMAIL_WORKERS', 3)

# Global thread pool for async email sending
email_executor = ThreadPoolExecutor(max_workers=MAX_EMAIL_WORKERS, thread_name_prefix="contact_email")

def send_contact_email_async(email_data):
    """Send contact form email in background thread"""
    try:
        if not SENDGRID_API_KEY:
            logger.error("SendGrid API key is not configured")
            return False
        
        # Create email with professional template
        mail = Mail(
            from_email=VERIFIED_SENDER_EMAIL,
            to_emails=ADMIN_EMAIL,
            subject=f"Contact Enquiry from {email_data['full_name']}",
            html_content=email_data['html_content']
        )
        
        # Add reply-to header
        mail.reply_to = email_data['reply_to_email']
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(mail)
        
        logger.info(f"Contact email sent successfully. Status: {response.status_code}")
        logger.info(f"Contact from: {email_data['full_name']} <{email_data['reply_to_email']}>")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send contact email: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        
        # Enhanced error logging
        if hasattr(e, 'response') and e.response:
            logger.error(f"SendGrid HTTP Status: {e.response.status_code}")
            logger.error(f"SendGrid Response: {e.response.body}")
        
        return False

def create_simple_professional_template(data, timestamp):
    """Create simple professional HTML email template matching the exact structure"""
    
    # Sanitize data
    first_name = html.escape(data.get('first_name', '').strip())
    last_name = html.escape(data.get('last_name', '').strip())
    email = html.escape(data.get('email', '').strip())
    company = html.escape(data.get('company', 'Not specified').strip())
    subject = html.escape(data.get('subject', 'General Inquiry').strip())
    message = html.escape(data.get('message', '').strip())
    phone = html.escape(data.get('phone', 'Not provided').strip())
    
    full_name = f"{first_name} {last_name}".strip()
    
    # Professional email template matching your exact structure
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Enquiry</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.5; color: #333333; background-color: #f5f5f5;">
    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f5f5f5; margin: 0; padding: 20px 0;">
        <tr>
            <td align="center" valign="top">
                <!-- Main Container -->
                <table cellpadding="0" cellspacing="0" border="0" width="600" style="max-width: 600px; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #ffffff; padding: 30px 30px 20px 30px; text-align: center;">
                            <h1 style="margin: 0; font-size: 24px; font-weight: 600; color: #4a5568; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;">
                                Contact Enquiry
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 0 30px 30px 30px;">
                            
                            <!-- Greeting -->
                            <div style="margin-bottom: 25px; font-size: 15px; color: #718096; line-height: 1.5;">
                                Hello Team,
                            </div>
                            
                            <div style="margin-bottom: 30px; font-size: 15px; color: #718096; line-height: 1.5;">
                                You have received a new enquiry from website.
                            </div>
                            
                            <!-- Contact Information Table -->
                            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f7fafc; border: 1px solid #e2e8f0; border-radius: 6px; margin: 25px 0;">
                                <tr>
                                    <td style="padding: 25px;">
                                        
                                        <!-- Name Row -->
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 15px;">
                                            <tr>
                                                <td width="100" style="font-weight: 600; color: #4a5568; padding-right: 15px; vertical-align: top; font-size: 14px;">
                                                    Name:
                                                </td>
                                                <td style="color: #2d3748; font-size: 14px;">
                                                    {full_name}
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Email Row -->
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 15px;">
                                            <tr>
                                                <td width="100" style="font-weight: 600; color: #4a5568; padding-right: 15px; vertical-align: top; font-size: 14px;">
                                                    Email:
                                                </td>
                                                <td style="color: #2d3748; font-size: 14px;">
                                                    <a href="mailto:{email}" style="color: #3182ce; text-decoration: none;">
                                                        {email}
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Company Row -->
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 15px;">
                                            <tr>
                                                <td width="100" style="font-weight: 600; color: #4a5568; padding-right: 15px; vertical-align: top; font-size: 14px;">
                                                    Company:
                                                </td>
                                                <td style="color: #2d3748; font-size: 14px;">
                                                    {company}
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Subject Row -->
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 15px;">
                                            <tr>
                                                <td width="100" style="font-weight: 600; color: #4a5568; padding-right: 15px; vertical-align: top; font-size: 14px;">
                                                    Subject:
                                                </td>
                                                <td style="color: #2d3748; font-size: 14px;">
                                                    {subject}
                                                </td>
                                            </tr>
                                        </table>
                                        
                                        <!-- Phone Row -->
                                        <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                            <tr>
                                                <td width="100" style="font-weight: 600; color: #4a5568; padding-right: 15px; vertical-align: top; font-size: 14px;">
                                                    Phone:
                                                </td>
                                                <td style="color: #2d3748; font-size: 14px;">
                                                    {phone}
                                                </td>
                                            </tr>
                                        </table>
                                        
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Message Section -->
                            <div style="margin: 30px 0 0 0;">
                                <div style="font-weight: 600; color: #4a5568; margin-bottom: 15px; font-size: 14px;">
                                    Message:
                                </div>
                                <div style="background-color: #f7fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 20px; color: #2d3748; line-height: 1.6; min-height: 60px; font-size: 14px;">
                                    {message if message.strip() else '<span style="color: #a0aec0; font-style: italic;">No message provided</span>'}
                                </div>
                            </div>
                            
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f7fafc; padding: 20px 30px; border-top: 1px solid #e2e8f0; font-size: 13px; color: #718096;">
                            
                            <div style="margin-bottom: 8px;">
                                <strong>Submitted:</strong> {timestamp}
                            </div>
                            <div style="margin-bottom: 8px;">
                                <strong>Source:</strong> Website Contact Form
                            </div>
                            <div>
                                <strong>Reply to:</strong> 
                                <a href="mailto:{email}" style="color: #3182ce; text-decoration: none;">
                                    {email}
                                </a>
                            </div>
                            
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    return html_content

class ContactFormAPIView(APIView):
    """
    Professional contact form API endpoint with async email sending
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Handle contact form submission"""
        try:
            data = request.data
            
            # Extract and validate required fields
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            email = data.get('email', '').strip()
            subject = data.get('subject', '').strip()
            message = data.get('message', '').strip()
            
            # Optional fields
            company = data.get('company', '').strip()
            phone = data.get('phone', '').strip()
            
            # Validate required fields
            if not all([first_name, last_name, email, subject]):
                logger.warning(f"Contact form validation failed - missing required fields from {request.META.get('REMOTE_ADDR')}")
                return self.error_response(
                    "Please fill in all required fields: First Name, Last Name, Email, and Subject."
                )
            
            # Validate email format
            try:
                validate_email(email)
            except ValidationError:
                logger.warning(f"Invalid email format attempted: {email}")
                return self.error_response("Please provide a valid email address.")
            
            # Additional email validation
            if len(email) > 254:
                return self.error_response("Email address is too long.")
            
            # Validate name lengths
            if len(first_name) > 50 or len(last_name) > 50:
                return self.error_response("Names must be less than 50 characters.")
            
            # Validate subject and message lengths
            if len(subject) > 200:
                return self.error_response("Subject must be less than 200 characters.")
                
            if len(message) > 2000:
                return self.error_response("Message must be less than 2000 characters.")
            
            # Validate phone number if provided
            if phone and len(phone) > 20:
                return self.error_response("Phone number must be less than 20 characters.")
            
            # Basic spam protection - check for suspicious patterns
            if self.is_spam_content(first_name, last_name, email, message):
                logger.warning(f"Potential spam detected from {email}")
                return self.error_response("Your message appears to contain spam content. Please revise and try again.")
            
            # Log the contact form submission
            full_name = f"{first_name} {last_name}"
            logger.info(f"Contact form submitted by {full_name} <{email}> - Subject: {subject}")
            
            # Generate timestamp with timezone
            timestamp = self.get_formatted_timestamp()
            
            # Create professional email template
            html_content = create_simple_professional_template(data, timestamp)
            
            # Prepare email data
            email_data = {
                'full_name': full_name,
                'reply_to_email': email,
                'subject': subject,
                'html_content': html_content
            }
            
            # Check SendGrid configuration
            if not SENDGRID_API_KEY:
                logger.error("SendGrid API key not configured - email cannot be sent")
                return self.success_response(
                    "Thank you for your message. We'll get back to you soon!"
                )
            
            # Send email asynchronously
            try:
                email_executor.submit(send_contact_email_async, email_data)
                logger.info(f"Contact email queued for {full_name} <{email}>")
            except Exception as e:
                logger.error(f"Failed to queue contact email: {str(e)}")
                # Don't fail the request if email queueing fails
            
            # Return immediate success response
            return self.success_response(
                "Thank you for reaching out! We've received your message and will respond within 24 hours."
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in contact form: {str(e)}")
            logger.error(f"Request data: {request.data}")
            return self.error_response(
                "We're experiencing technical difficulties. Please try again later or contact us directly."
            )
    
    def get(self, request):
        """Health check and configuration status"""
        return Response({
            "status": "healthy",
            "service": "Contact Form API",
            "sendgrid_configured": bool(SENDGRID_API_KEY),
            "admin_email": ADMIN_EMAIL,
            "sender_email": VERIFIED_SENDER_EMAIL,
            "version": "2.0"
        })
    
    def is_spam_content(self, first_name, last_name, email, message):
        """Basic spam detection"""
        # Check for suspicious patterns
        spam_indicators = [
            len(message) > 0 and len(set(message.lower())) < 10,  # Too repetitive
            'http://' in message.lower() or 'https://' in message.lower(),  # Contains URLs
            message.count('!') > 5,  # Too many exclamation marks
            any(word in message.lower() for word in ['viagra', 'casino', 'lottery', 'winner']),  # Spam words
        ]
        
        return sum(spam_indicators) >= 2  # Trigger if 2 or more indicators
    
    def success_response(self, message, data=None):
        """Standardized success response"""
        return Response({
            "success": True,
            "message": message,
            "data": data or {}
        }, status=status.HTTP_200_OK)
    
    def error_response(self, message, errors=None):
        """Standardized error response"""
        return Response({
            "success": False,
            "message": message,
            "errors": errors or {}
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_formatted_timestamp(self):
        """Get properly formatted timestamp"""
        try:
            # Use Asia/Kolkata timezone (adjust as needed for your location)
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz)
            timestamp = now.strftime("%B %d, %Y at %I:%M %p (%Z)")
            return timestamp
        except Exception as e:
            logger.error(f"Timezone conversion failed: {e}")
            # Fallback to UTC
            now = datetime.utcnow()
            return now.strftime("%B %d, %Y at %I:%M %p UTC")

# Test function for SendGrid configuration
def test_contact_email():
    """Test function to verify contact email setup"""
    try:
        if not SENDGRID_API_KEY:
            logger.error("SendGrid API key is not configured")
            return False
            
        test_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'company': 'Test Company',
            'phone': '+1234567890',
            'subject': 'Test Contact Form',
            'message': 'This is a test message to verify the contact form email setup.'
        }
        
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p UTC")
        html_content = create_simple_professional_template(test_data, timestamp)
        
        email_data = {
            'full_name': 'Test User',
            'reply_to_email': 'test@example.com',
            'subject': 'Test Contact Form',
            'html_content': html_content
        }
        
        result = send_contact_email_async(email_data)
        
        if result:
            logger.info("Contact email test successful")
            return True
        else:
            logger.error("Contact email test failed")
            return False
            
    except Exception as e:
        logger.error(f"Contact email test failed: {e}")
        return False

# Additional utility functions
def validate_contact_data(data):
    """Validate contact form data"""
    errors = {}
    
    # Required fields
    required_fields = ['first_name', 'last_name', 'email', 'subject']
    for field in required_fields:
        if not data.get(field, '').strip():
            errors[field] = f"{field.replace('_', ' ').title()} is required."
    
    # Email validation
    email = data.get('email', '').strip()
    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = "Please provide a valid email address."
    
    # Length validations
    if len(data.get('first_name', '')) > 50:
        errors['first_name'] = "First name must be less than 50 characters."
    
    if len(data.get('last_name', '')) > 50:
        errors['last_name'] = "Last name must be less than 50 characters."
    
    if len(data.get('subject', '')) > 200:
        errors['subject'] = "Subject must be less than 200 characters."
    
    if len(data.get('message', '')) > 2000:
        errors['message'] = "Message must be less than 2000 characters."
    
    if len(data.get('phone', '')) > 20:
        errors['phone'] = "Phone number must be less than 20 characters."
    
    return errors

def send_auto_reply_email(user_email, user_name):
    """Send auto-reply confirmation to user"""
    try:
        if not SENDGRID_API_KEY:
            return False
        
        auto_reply_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #f8f9fa; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .footer {{ background: #f8f9fa; padding: 15px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Thank you for contacting us!</h2>
                </div>
                <div class="content">
                    <p>Dear {user_name},</p>
                    <p>We have received your message and will get back to you within 24 hours.</p>
                    <p>Thank you for your interest in our services.</p>
                    <p>Best regards,<br>The Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated response. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        mail = Mail(
            from_email=VERIFIED_SENDER_EMAIL,
            to_emails=user_email,
            subject="Thank you for contacting us",
            html_content=auto_reply_content
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(mail)
        
        logger.info(f"Auto-reply sent to {user_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send auto-reply: {e}")
        return False