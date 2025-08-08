import logging
from datetime import datetime
import pytz
from threading import Thread
from queue import Queue
import asyncio
from concurrent.futures import ThreadPoolExecutor

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

# Replace these with environment variables in production!
SENDGRID_API_KEY = settings.SENDGRID_API_KEY
ADMIN_EMAIL = 'theerthakk467@gmail.com'
# Use verified sender email - change this to your verified SendGrid sender
VERIFIED_SENDER_EMAIL = 'noreply@advolcano.io'  # Must be verified in SendGrid

# Global thread pool for async email sending
email_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="email_sender")

def send_email_async(email_data):
    """Send email in background thread with enhanced error handling"""
    try:
        # Validate API key exists
        if not SENDGRID_API_KEY:
            logger.error("SendGrid API key is not set")
            return
        
        mail = Mail(
            from_email=VERIFIED_SENDER_EMAIL,  # Use verified sender
            to_emails=ADMIN_EMAIL,
            subject='[AdVolcano] New Demo Request',
            html_content=email_data['content']
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(mail)
        
        logger.info(f"Email sent successfully. Status: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        
    except Exception as e:
        logger.error(f"Background email sending failed: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        
        # Enhanced error logging for debugging
        if hasattr(e, 'response') and e.response:
            logger.error(f"HTTP Status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.body}")
        
        # Log API key status (first 10 chars only for security)
        if SENDGRID_API_KEY:
            logger.info(f"API Key present (starts with): {SENDGRID_API_KEY[:10]}...")
        else:
            logger.error("API Key is missing!")

def test_sendgrid_connection():
    """Test function to verify SendGrid setup"""
    try:
        if not SENDGRID_API_KEY:
            logger.error("SendGrid API key is not configured")
            return False
            
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        mail = Mail(
            from_email=VERIFIED_SENDER_EMAIL,
            to_emails=ADMIN_EMAIL,
            subject='SendGrid Connection Test',
            html_content='<p>This is a test email to verify SendGrid configuration.</p>'
        )
        response = sg.send(mail)
        logger.info(f"SendGrid test successful: Status {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"SendGrid test failed: {e}")
        return False

class RequestDemoAPIView(APIView):
    """
    Optimized endpoint for demo requests with async email sending.
    """

    def post(self, request):
        data = request.data
        interest = data.get('interest')
        full_name = data.get('full_name')
        email = data.get('email')
        company = data.get('company', 'N/A')
        message = data.get('message', 'N/A')

        # Validate required fields (fast validation)
        if not all([interest, full_name, email]):
            return Response(
                {"error": "interest, full_name, and email are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Enhanced email format validation
        if not email or '@' not in email or '.' not in email.split('@')[-1]:
            return Response(
                {"error": "Please provide a valid email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate email length and basic format
        if len(email) > 254 or len(email.split('@')[0]) > 64:
            return Response(
                {"error": "Email address is too long."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Log the demo request (minimal logging)
        logger.info(f"Demo request received from {email} for {interest}")

        # Pre-calculate timestamp (optimize timezone handling)
        try:
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz)
            timestamp = now.strftime("on %d %b, %Y %I:%M:%S %p UTC%z")
            timestamp = timestamp[:-2] + ':' + timestamp[-2:]
        except Exception as e:
            logger.error(f"Timezone conversion failed: {e}")
            # Fallback to UTC
            now = datetime.utcnow()
            timestamp = now.strftime("on %d %b, %Y %I:%M:%S %p UTC")

        # Email content with improved HTML structure
        email_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Demo Request</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <div style="max-width: 650px; margin: 0 auto; padding: 40px; background-color: #f9f9f9;">
        <div style="background-color: white; padding: 32px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <h2 style="color: #4a5568; font-size: 20px; font-weight: 600; margin: 0 0 24px 0; display: flex; align-items: center;">
                <span style="margin-right: 8px;">📩</span> New Demo Request
            </h2>
            <p style="font-size: 16px; color: #2d3748; margin: 0 0 24px 0;">
                You've received a new demo request from <a href="https://advolcano.io" style="color: #3182ce; text-decoration: none;">advolcano.io</a>
            </p>
            <div style="background-color: #f7fafc; padding: 20px; border-radius: 6px; margin: 24px 0;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #4a5568; font-weight: 600; width: 140px; vertical-align: top;">Interest</td>
                        <td style="padding: 8px 0; color: #2d3748;">: {interest}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #4a5568; font-weight: 600; vertical-align: top;">Full Name</td>
                        <td style="padding: 8px 0; color: #2d3748;">: {full_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #4a5568; font-weight: 600; vertical-align: top;">Email</td>
                        <td style="padding: 8px 0; color: #2d3748;">: <a href="mailto:{email}" style="color: #3182ce; text-decoration: none;">{email}</a></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #4a5568; font-weight: 600; vertical-align: top;">Company</td>
                        <td style="padding: 8px 0; color: #2d3748;">: {company}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #4a5568; font-weight: 600; vertical-align: top;">Message</td>
                        <td style="padding: 8px 0; color: #2d3748;">: {message}</td>
                    </tr>
                </table>
            </div>
            <p style="margin: 24px 0 0 0; font-size: 14px; color: #718096;">
                This demo request generated from <strong>Advolcano.io</strong> {timestamp}
            </p>
        </div>
    </div>
</body>
</html>"""

        # Check if SendGrid is properly configured
        if not SENDGRID_API_KEY:
            logger.error("SendGrid API key not configured - email will not be sent")
            return Response(
                {"message": "Demo request submitted. Our team will contact you soon."},
                status=status.HTTP_200_OK,
            )

        # Send email asynchronously (non-blocking)
        try:
            email_data = {'content': email_content}
            email_executor.submit(send_email_async, email_data)
            logger.info(f"Email queued for sending to {ADMIN_EMAIL}")
        except Exception as e:
            logger.error(f"Failed to queue email: {e}")
            # Don't fail the request if email queueing fails

        # Return response immediately without waiting for email
        return Response(
            {"message": "Demo request submitted successfully. Our team will contact you soon."},
            status=status.HTTP_200_OK,
        )

    def get(self, request):
        """Health check endpoint"""
        return Response({
            "status": "healthy",
            "sendgrid_configured": bool(SENDGRID_API_KEY),
            "admin_email": ADMIN_EMAIL,
            "sender_email": VERIFIED_SENDER_EMAIL
        })


# Management command to test SendGrid configuration
# Save this in management/commands/test_sendgrid.py
"""
from django.core.management.base import BaseCommand
from your_app.views import test_sendgrid_connection

class Command(BaseCommand):
    help = 'Test SendGrid email configuration'

    def handle(self, *args, **options):
        self.stdout.write('Testing SendGrid configuration...')
        if test_sendgrid_connection():
            self.stdout.write(self.style.SUCCESS('SendGrid test passed!'))
        else:
            self.stdout.write(self.style.ERROR('SendGrid test failed!'))
"""


# Alternative implementation using Celery for production environments
"""
# Add this to your tasks.py if using Celery
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_demo_email_task(self, email_content, recipient_email=None):
    try:
        mail = Mail(
            from_email=VERIFIED_SENDER_EMAIL,
            to_emails=recipient_email or ADMIN_EMAIL,
            subject='[AdVolcano] New Demo Request',
            html_content=email_content
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(mail)
        logger.info(f"Celery email sent successfully. Status: {response.status_code}")
        return f"Email sent with status: {response.status_code}"
    except Exception as e:
        logger.error(f"Celery email failed: {str(e)}")
        # Retry the task if it fails
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying email send (attempt {self.request.retries + 1})")
            raise self.retry(exc=e)
        else:
            logger.error("Max retries reached for email sending")
            raise

# Then in your view, replace the executor.submit line with:
# send_demo_email_task.delay(email_content)
"""


# Environment variables setup guide
"""
# Add these to your .env file or environment variables:

# SendGrid Configuration
SENDGRID_API_KEY=your_sendgrid_api_key_here

# Email Configuration
ADMIN_EMAIL=basilsabu268@gmail.com
VERIFIED_SENDER_EMAIL=basilsabu268@gmail.com

# Django Settings
DEBUG=False  # Set to False in production
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# In your settings.py:
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
"""