import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Set up logging
logger = logging.getLogger(__name__)

# Replace these with environment variables in production!
ADMIN_EMAIL = 'theerthakk467@gmail.com'  # Replace with actual admin email

class RequestDemoAPIView(APIView):
    """
    Endpoint for users to submit a demo request form.
    Sends a notification email to the admin with user details.
    """

    def post(self, request):
        data = request.data
        interest = data.get('interest')
        full_name = data.get('full_name')
        email = data.get('email')
        company = data.get('company', 'N/A')
        message = data.get('message', 'N/A')

        # Validate required fields
        if not all([interest, full_name, email]):
            return Response(
                {"error": "interest, full_name, and email are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Log the demo request
        logger.info(
            f"Demo Request: interest={interest}, full_name={full_name}, "
            f"email={email}, company={company}, message={message}"
        )

        # HTML email content (professional layout)
        email_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #2c3e50; text-align: center;">📩 New Demo Request</h2>
                <p style="font-size: 16px; color: #333;"><strong>You've received a new demo request from the website.</strong></p>

                <table style="width: 100%; margin-top: 20px; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold; color: #555;">Interest:</td>
                        <td style="padding: 8px; color: #000;">{interest}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; color: #555;">Full Name:</td>
                        <td style="padding: 8px; color: #000;">{full_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; color: #555;">Email:</td>
                        <td style="padding: 8px; color: #000;">{email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; color: #555;">Company:</td>
                        <td style="padding: 8px; color: #000;">{company}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold; color: #555;">Message:</td>
                        <td style="padding: 8px; color: #000; white-space: pre-line;">{message}</td>
                    </tr>
                </table>

                <p style="margin-top: 30px; font-size: 14px; color: #777;">This is an automated notification from <strong>AdVolcano</strong>.</p>
            </div>
        """

        # Send the email using SendGrid
        try:
            mail = Mail(
                from_email='noreply@advolcano.io',
                to_emails=ADMIN_EMAIL,
                subject='[AdVolcano] New Demo Request',
                html_content=email_content
            )
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(mail)
            logger.info(f"Admin notified of demo request via email. SendGrid status: {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending email to admin: {str(e)}")
            return Response(
                {"error": "Failed to notify admin via email."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "Demo request submitted. Our team will contact you soon."},
            status=status.HTTP_200_OK,
        )
