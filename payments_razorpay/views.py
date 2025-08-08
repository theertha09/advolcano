import logging
import razorpay
import requests
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings

# === API KEYS & CONFIG ===
SENDGRID_API_KEY = settings.SENDGRID_API_KEY
RAZORPAY_KEY_ID = settings.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = settings.RAZORPAY_KEY_SECRET
FIXER_API_KEY = settings.FIXER_API_KEY
ADMIN_EMAIL = settings.ADMIN_EMAIL
FROM_EMAIL = settings.FROM_EMAIL
logger = logging.getLogger(__name__)

# === Logging configuration ===
logging.basicConfig(
    filename="payment_logs.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# === Helper function to send admin email ===
def send_admin_notification(order_details, payment_details=None, email_type="payment_created"):
    """
    Send admin notification email for different payment events - Razorpay style format
    """
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        
        if email_type == "payment_verified":
            subject = f"Razorpay : Payment in advolcano.io (Order ID : {payment_details.get('razorpay_order_id', 'N/A')}) State: Payment Completed"
            
            # Format timestamp if available
            timestamp = payment_details.get('timestamp', 'Just now')
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp).strftime('%d %b, %Y %I:%M:%S %p UTC')
            
            email_body = f"""Hello,

You have received a payment against Order ID : {payment_details.get('razorpay_order_id', 'N/A')} in advolcano.io

Order Confirmation Details
Payment ID      : {payment_details.get('razorpay_payment_id', 'N/A')}
Paid On         : {timestamp}
Total Amount    : INR {order_details.get('total_amount', 0):.2f}

Order Details
Shop            : advolcano.io
Order ID        : {payment_details.get('razorpay_order_id', 'N/A')}
Amount          : INR {order_details.get('total_amount', 0):.2f}

--------------------------------------------------------

Payment Summary
--------------------------------------------------------
Advolcano Name  : {order_details.get('name', 'N/A')}
Advolcano Email : {order_details.get('email', 'N/A')}

Amount (USD)    : ${order_details.get('amount_usd', 0):.2f}
Amount (INR)    : ₹{order_details.get('amount_inr', 0):.2f}
Platform Fee    : ₹{order_details.get('commission', 0):.2f}
TAX             : ₹{order_details.get('gst', 0):.2f}
Total Amount    : ₹{order_details.get('total_amount', 0):.2f}

Best regards,
Advolcano.io Payment System
"""
        elif email_type == "payment_failed":
            subject = f"Razorpay : Payment in advolcano.io (Order ID : {payment_details.get('razorpay_order_id', 'N/A')}) State: Payment Failed"
            
            # Format timestamp if available
            timestamp = payment_details.get('timestamp', 'Just now')
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp).strftime('%d %b, %Y %I:%M:%S %p UTC')
            
            email_body = f"""Hello,

⚠️ PAYMENT FAILED ALERT ⚠️

A payment attempt has failed for Order ID : {payment_details.get('razorpay_order_id', 'N/A')} in advolcano.io

Failed Payment Details
Order ID        : {payment_details.get('razorpay_order_id', 'N/A')}
Failed On       : {timestamp}
Failure Reason  : {payment_details.get('failure_reason', 'Signature verification failed')}
Total Amount    : INR {order_details.get('total_amount', 0):.2f}

--------------------------------------------------------

Customer Details
--------------------------------------------------------
Advolcano Name  : {order_details.get('name', 'N/A')}
Advolcano Email : {order_details.get('email', 'N/A')}

Amount (USD)    : ${order_details.get('amount_usd', 0):.2f}
Amount (INR)    : ₹{order_details.get('amount_inr', 0):.2f}
Platform Fee    : ₹{order_details.get('commission', 0):.2f}
TAX             : ₹{order_details.get('gst', 0):.2f}
Total Amount    : ₹{order_details.get('total_amount', 0):.2f}

--------------------------------------------------------

Action Required:
- Customer may need assistance with payment
- Check if customer needs to retry payment
- Monitor for multiple failed attempts

Best regards,
Advolcano.io Payment System
"""
        else:  # payment_created
            subject = f"Razorpay : Payment in advolcano.io (Order ID : {order_details.get('order_id', 'N/A')}) State: Payment Initiated"
            email_body = f"""Hello,

A new payment order has been created in advolcano.io.

--------------------------------------------------------
Order Details
--------------------------------------------------------
Shop            : advolcano.io
Order ID        : {order_details.get('order_id', 'N/A')}
Amount          : INR {order_details.get('total_amount', 0):.2f}
Status          : Payment Initiated

--------------------------------------------------------
Payment Summary
--------------------------------------------------------
Advolcano Name  : {order_details.get('name', 'N/A')}
Advolcano Email : {order_details.get('email', 'N/A')}

Amount (USD)    : ${order_details.get('amount_usd', 0):.2f}
Amount (INR)    : ₹{order_details.get('amount_inr', 0):.2f}
Platform Fee    : ₹{order_details.get('commission', 0):.2f}
TAX             : ₹{order_details.get('gst', 0):.2f}
Total Amount    : ₹{order_details.get('total_amount', 0):.2f}

--------------------------------------------------------

⏳ Waiting for customer to complete payment...

Best regards,
Advolcano.io Payment System
"""

        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=ADMIN_EMAIL,
            subject=subject,
            plain_text_content=email_body
        )
        
        response = sg.send(message)
        logger.info(f"✅ Admin email sent successfully - Type: {email_type}, Status Code: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send admin email ({email_type}): {str(e)}")
        return False

# === Helper function to send user payment success email ===
def send_user_success_email(order_details, payment_details):
    """
    Send payment success confirmation email to user
    """
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        
        # Format timestamp
        timestamp = payment_details.get('timestamp', datetime.now())
        if isinstance(timestamp, (int, float)):
            formatted_time = datetime.fromtimestamp(timestamp).strftime('%B %d, %Y at %I:%M %p IST')
        else:
            formatted_time = datetime.now().strftime('%B %d, %Y at %I:%M %p IST')
        
        # Updated subject line to use "Payment Process"
        subject = f"Payment Process Complete - Order {payment_details.get('razorpay_order_id', 'N/A')} | AdVolcano"
        
        # Create HTML email body with "Payment Process" naming
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ padding: 30px; }}
        .order-id {{ background-color: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center; font-weight: bold; }}
        .section {{ margin-bottom: 30px; }}
        .section h3 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 5px; margin-bottom: 15px; }}
        .details-row {{ display: flex; justify-content: space-between; margin: 10px 0; padding: 8px 0; }}
        .details-label {{ font-weight: 500; color: #555; }}
        .details-value {{ color: #333; }}
        .total-row {{ background-color: #4CAF50; color: white; padding: 15px; margin: 10px 0; border-radius: 5px; font-weight: bold; font-size: 18px; }}
        .next-steps {{ background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 20px; margin: 20px 0; }}
        .next-steps h3 {{ color: #856404; margin-top: 0; }}
        .next-steps ol {{ color: #856404; }}
        .important {{ background-color: #e7f3ff; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; background-color: #333; color: white; }}
        .support-link {{ color: #4CAF50; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Payment Process Complete</h1>
        </div>
        
        <div class="content">
            <p>Dear <strong>{order_details.get('name', 'N/A')}</strong>,</p>
            
            <p>Thank you for your order with <a href="https://advolcano.io" style="color: #4CAF50; text-decoration: none;">advolcano.io</a>. We have received your payment with the following details:</p>
            
            <div class="order-id">
                Order ID: {payment_details.get('razorpay_order_id', 'N/A')}
            </div>
            
            <div class="section">
                <h3>Customer Details</h3>
                <div class="details-row">
                    <span class="details-label">AdVolcano Name :</span>
                    <span class="details-value">{order_details.get('name', 'N/A')}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">AdVolcano Email :</span>
                    <span class="details-value">{order_details.get('email', 'N/A')}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">Date & Time :</span>
                    <span class="details-value">{formatted_time}</span>
                </div>
            </div>
            
            <div class="section">
                <h3>Payment Summary</h3>
                <div class="details-row">
                    <span class="details-label">Base Amount (USD)</span>
                    <span class="details-value">${order_details.get('amount_usd', 0):.2f}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">Base Amount (INR)</span>
                    <span class="details-value">₹{order_details.get('amount_inr', 0):.2f}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">Platform Fee</span>
                    <span class="details-value">₹{order_details.get('commission', 0):.2f}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">TAX (GST - 18%)</span>
                    <span class="details-value">₹{order_details.get('gst', 0):.2f}</span>
                </div>
                <div class="total-row">
                    <div style="display: flex; justify-content: space-between;">
                        <span>TOTAL AMOUNT:</span>
                        <span>₹{order_details.get('total_amount', 0):.2f}</span>
                    </div>
                </div>
            </div>
            
            <div class="next-steps">
                <h3>Next Steps</h3>
                <ol>
                    <li>We'll credit your AdVolcano wallet within 24hrs</li>
                </ol>
            </div>
            
            <div class="important">
                <strong>Important:</strong> This order will reflect in your wallet in 24 to 48 hours. For any communication related to this payment please quote your payment order ID <strong>{payment_details.get('razorpay_order_id', 'N/A')}</strong>.
            </div>
            
            <p>Need help? Contact us at <a href="mailto:support@advolcano.io" class="support-link">support@advolcano.io</a></p>
            
            <p>Best regards,<br>
            <strong>AdVolcano Team</strong></p>
        </div>
        
        <div class="footer">
            © 2025 AdVolcano. All rights reserved.
        </div>
    </div>
</body>
</html>
"""
        
        # Plain text version
        plain_text_body = f"""
Payment Process Complete

Dear {order_details.get('name', 'N/A')},

Thank you for your order with advolcano.io. We have received your payment with the following details:

Order ID: {payment_details.get('razorpay_order_id', 'N/A')}

Customer Details
AdVolcano Name : {order_details.get('name', 'N/A')}
AdVolcano Email : {order_details.get('email', 'N/A')}
Date & Time : {formatted_time}

Payment Summary
Base Amount (USD): ${order_details.get('amount_usd', 0):.2f}
Base Amount (INR): ₹{order_details.get('amount_inr', 0):.2f}
Platform Fee: ₹{order_details.get('commission', 0):.2f}
TAX (GST - 18%): ₹{order_details.get('gst', 0):.2f}
TOTAL AMOUNT: ₹{order_details.get('total_amount', 0):.2f}

Next Steps
1. Payment confirmed on Razorpay gateway
2. We'll credit your AdVolcano wallet within 24hrs
3. Order will be processed after payment confirmation

Important: This order will reflect in your wallet in 24 to 48 hours. For any communication related to this payment please quote your payment order ID {payment_details.get('razorpay_order_id', 'N/A')}.

Need help? Contact us at support@advolcano.io

Best regards,
AdVolcano Team

© 2025 AdVolcano. All rights reserved.
"""

        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=order_details.get('email'),
            subject=subject,
            plain_text_content=plain_text_body,
            html_content=html_body
        )
        
        response = sg.send(message)
        logger.info(f"✅ User success email sent to {order_details.get('email')} - Status Code: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send user success email: {str(e)}")
        return False

# === NEW: Helper function to send user payment failure email ===
def send_user_failure_email(order_details, payment_details):
    """
    Send payment failure notification email to user
    """
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        
        # Format timestamp
        timestamp = payment_details.get('timestamp', datetime.now())
        if isinstance(timestamp, (int, float)):
            formatted_time = datetime.fromtimestamp(timestamp).strftime('%B %d, %Y at %I:%M %p IST')
        else:
            formatted_time = datetime.now().strftime('%B %d, %Y at %I:%M %p IST')
        
        subject = f"Payment Failed - Order {payment_details.get('razorpay_order_id', 'N/A')} | AdVolcano"
        
        # Create HTML email body for payment failure
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ padding: 30px; }}
        .order-id {{ background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center; font-weight: bold; color: #721c24; }}
        .section {{ margin-bottom: 30px; }}
        .section h3 {{ color: #333; border-bottom: 2px solid #dc3545; padding-bottom: 5px; margin-bottom: 15px; }}
        .details-row {{ display: flex; justify-content: space-between; margin: 10px 0; padding: 8px 0; }}
        .details-label {{ font-weight: 500; color: #555; }}
        .details-value {{ color: #333; }}
        .total-row {{ background-color: #dc3545; color: white; padding: 15px; margin: 10px 0; border-radius: 5px; font-weight: bold; font-size: 18px; }}
        .retry-steps {{ background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 20px; margin: 20px 0; }}
        .retry-steps h3 {{ color: #856404; margin-top: 0; }}
        .retry-steps ol {{ color: #856404; }}
        .error-info {{ background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0; color: #721c24; }}
        .footer {{ text-align: center; padding: 20px; background-color: #333; color: white; }}
        .support-link {{ color: #dc3545; text-decoration: none; }}
        .retry-button {{ display: inline-block; background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Payment Failed</h1>
        </div>
        
        <div class="content">
            <p>Dear <strong>{order_details.get('name', 'N/A')}</strong>,</p>
            
            <p>We're sorry to inform you that your payment for <a href="https://advolcano.io" style="color: #dc3545; text-decoration: none;">advolcano.io</a> could not be processed.</p>
            
            <div class="order-id">
                Order ID: {payment_details.get('razorpay_order_id', 'N/A')}
            </div>
            
            <div class="error-info">
                <strong>Payment Status:</strong> Failed<br>
                <strong>Reason:</strong> {payment_details.get('failure_reason', 'Payment verification failed')}<br>
                <strong>Failed On:</strong> {formatted_time}
            </div>
            
            <div class="section">
                <h3>Order Details</h3>
                <div class="details-row">
                    <span class="details-label">AdVolcano Name :</span>
                    <span class="details-value">{order_details.get('name', 'N/A')}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">AdVolcano Email :</span>
                    <span class="details-value">{order_details.get('email', 'N/A')}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">Order ID :</span>
                    <span class="details-value">{payment_details.get('razorpay_order_id', 'N/A')}</span>
                </div>
            </div>
            
            <div class="section">
                <h3>Payment Summary</h3>
                <div class="details-row">
                    <span class="details-label">Base Amount (USD)</span>
                    <span class="details-value">${order_details.get('amount_usd', 0):.2f}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">Base Amount (INR)</span>
                    <span class="details-value">₹{order_details.get('amount_inr', 0):.2f}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">Platform Fee</span>
                    <span class="details-value">₹{order_details.get('commission', 0):.2f}</span>
                </div>
                <div class="details-row">
                    <span class="details-label">TAX (GST - 18%)</span>
                    <span class="details-value">₹{order_details.get('gst', 0):.2f}</span>
                </div>
                <div class="total-row">
                    <div style="display: flex; justify-content: space-between;">
                        <span>TOTAL AMOUNT:</span>
                        <span>₹{order_details.get('total_amount', 0):.2f}</span>
                    </div>
                </div>
            </div>
            
            <div class="retry-steps">
                <h3>What to do next?</h3>
                <ol>
                    <li>Check your internet connection and try again</li>
                    <li>Ensure you have sufficient balance in your payment method</li>
                    <li>Try using a different payment method (card/UPI/net banking)</li>
                    <li>Contact your bank if the issue persists</li>
                    <li>Contact our support team for assistance</li>
                </ol>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="https://advolcano.io/retry-payment?order_id={payment_details.get('razorpay_order_id', 'N/A')}" class="retry-button">Retry Payment</a>
                </div>
            </div>
            
            <p>If you continue to experience issues, please contact us at <a href="mailto:support@advolcano.io" class="support-link">support@advolcano.io</a> with your Order ID: <strong>{payment_details.get('razorpay_order_id', 'N/A')}</strong></p>
            
            <p>Best regards,<br>
            <strong>AdVolcano Team</strong></p>
        </div>
        
        <div class="footer">
            © 2025 AdVolcano. All rights reserved.
        </div>
    </div>
</body>
</html>
"""
        
        # Plain text version
        plain_text_body = f"""
⚠️ Payment Failed

Dear {order_details.get('name', 'N/A')},

We're sorry to inform you that your payment for advolcano.io could not be processed.

Order ID: {payment_details.get('razorpay_order_id', 'N/A')}

Payment Status: Failed
Reason: {payment_details.get('failure_reason', 'Payment verification failed')}
Failed On: {formatted_time}

Order Details
AdVolcano Name : {order_details.get('name', 'N/A')}
AdVolcano Email : {order_details.get('email', 'N/A')}
Order ID : {payment_details.get('razorpay_order_id', 'N/A')}

Payment Summary
Base Amount (USD): ${order_details.get('amount_usd', 0):.2f}
Base Amount (INR): ₹{order_details.get('amount_inr', 0):.2f}
Platform Fee: ₹{order_details.get('commission', 0):.2f}
TAX (GST - 18%): ₹{order_details.get('gst', 0):.2f}
TOTAL AMOUNT: ₹{order_details.get('total_amount', 0):.2f}

What to do next?
1. Check your internet connection and try again
2. Ensure you have sufficient balance in your payment method
3. Try using a different payment method (card/UPI/net banking)
4. Contact your bank if the issue persists
5. Contact our support team for assistance

Retry Payment: https://advolcano.io/retry-payment?order_id={payment_details.get('razorpay_order_id', 'N/A')}

If you continue to experience issues, please contact us at support@advolcano.io with your Order ID: {payment_details.get('razorpay_order_id', 'N/A')}

Best regards,
AdVolcano Team

© 2025 AdVolcano. All rights reserved.
"""

        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=order_details.get('email'),
            subject=subject,
            plain_text_content=plain_text_body,
            html_content=html_body
        )
        
        response = sg.send(message)
        logger.info(f"✅ User failure email sent to {order_details.get('email')} - Status Code: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send user failure email: {str(e)}")
        return False

# === Serializers ===
class PaymentSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    amount_usd = serializers.FloatField(min_value=0.01)
    amount_inr = serializers.FloatField(min_value=0.01)
    commission = serializers.FloatField(min_value=0.0)
    gst = serializers.FloatField(min_value=0.0)
    total_amount = serializers.FloatField(min_value=0.01)

class AdminSetupSerializer(serializers.Serializer):
    admin_name = serializers.CharField(max_length=255)
    admin_email = serializers.EmailField()
    sendgrid_api_key = serializers.CharField(max_length=500)
    razorpay_key_id = serializers.CharField(max_length=100)
    razorpay_key_secret = serializers.CharField(max_length=100)
    from_email = serializers.EmailField()

# === Admin Setup API ===
class AdminSetupAPIView(APIView):
    """
    API endpoint to configure admin settings
    """
    def post(self, request):
        serializer = AdminSetupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        
        try:
            # Test SendGrid API key
            test_sg = SendGridAPIClient(data['sendgrid_api_key'])
            test_message = Mail(
                from_email=data['from_email'],
                to_emails=data['admin_email'],
                subject="AdVolcano Admin Setup Test",
                plain_text_content="This is a test email to verify your SendGrid configuration is working correctly."
            )
            
            # Send test email
            response = test_sg.send(test_message)
            
            if response.status_code not in [200, 202]:
                return Response({
                    "error": "SendGrid test failed",
                    "details": f"Status code: {response.status_code}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Test Razorpay credentials
            test_client = razorpay.Client(auth=(data['razorpay_key_id'], data['razorpay_key_secret']))
            
            # Create a test order (₹1)
            test_order_data = {
                "amount": 100,  # ₹1 in paise
                "currency": "INR",
                "payment_capture": 1,
                "notes": {
                    "test": "admin_setup_test"
                }
            }
            
            test_order = test_client.order.create(data=test_order_data)
            
            if not test_order.get('id'):
                return Response({
                    "error": "Razorpay test failed",
                    "details": "Could not create test order"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Log successful setup
            logger.info(f"✅ Admin setup completed - Admin: {data['admin_name']} ({data['admin_email']})")
            
            # Here you would typically save these credentials to your database
            # For now, we'll just return success response
            
            return Response({
                "status": "Admin setup completed successfully",
                "admin_name": data['admin_name'],
                "admin_email": data['admin_email'],
                "from_email": data['from_email'],
                "sendgrid_test": "✅ Passed",
                "razorpay_test": "✅ Passed",
                "test_order_id": test_order.get('id'),
                "message": "All configurations are working correctly. You can now process payments."
            }, status=status.HTTP_200_OK)
            
        except razorpay.errors.RazorpayError as e:
            logger.error(f"❌ Razorpay test failed: {str(e)}")
            return Response({
                "error": "Razorpay configuration failed",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"❌ Admin setup failed: {str(e)}")
            return Response({
                "error": "Admin setup failed",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """
        Get current admin configuration status
        """
        return Response({
            "current_admin_email": ADMIN_EMAIL,
            "current_from_email": FROM_EMAIL,
            "sendgrid_configured": bool(SENDGRID_API_KEY),
            "razorpay_configured": bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET),
            "status": "Configuration active"
        }, status=status.HTTP_200_OK)

class CreatePaymentAPIView(APIView):
    def post(self, request):
        serializer = PaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        total_amount_paise = int(round(data['total_amount'] * 100))  # Convert to paise

        try:
            client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

            order_data = {
                "amount": total_amount_paise,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {
                    "name": data['name'],
                    "email": data['email'],
                    "amount_usd": str(data['amount_usd']),
                    "amount_inr": str(data['amount_inr']),
                    "commission": str(data['commission']),
                    "gst": str(data['gst']),
                    "total_amount": str(data['total_amount']),
                }
            }

            order = client.order.create(data=order_data)

            logging.info(
                f"Order created: name={data['name']} email={data['email']} "
                f"USD={data['amount_usd']} INR={data['amount_inr']} "
                f"Commission={data['commission']} GST={data['gst']} "
                f"Total={data['total_amount']} OrderID={order.get('id')}"
            )

            # === Send ONLY Admin Email (same template as before) ===
            subject = f"Payment in advolcano.io (Order ID : {order.get('id')}) State: Payment Initiated"

            email_body = f"""
Hello Admin,

A new payment order has been created in advolcano.io.

--------------------------------------------------------
Order Details
--------------------------------------------------------
Shop            : advolcano.io
Order ID        : {order.get('id')}
Amount          : INR {data['total_amount']:.2f}

--------------------------------------------------------
Payment Summary
--------------------------------------------------------
Advolcano Name  : {data['name']}
Advolcano Email : {data['email']}

Amount (USD)    : ${data['amount_usd']:.2f}
Amount (INR)    : ₹{data['amount_inr']:.2f}
Platform Fee    : ₹{data['commission']:.2f}
TAX             : ₹{data['gst']:.2f}
Total Amount    : ₹{data['total_amount']:.2f}

--------------------------------------------------------

Best regards,
Advolcano.io Payments Team
"""

            try:
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                message = Mail(
                    from_email=FROM_EMAIL,
                    to_emails=["admin@advolcano.io", "theerthakk467@gmail.com"],  # Admin + Basil
                    subject=subject,
                    plain_text_content=email_body
                )
                sg.send(message)
                logging.info("Admin email sent successfully")
            except Exception as e:
                logging.error(f"Failed to send admin email: {e}")

            return Response({
                "order_id": order.get("id"),
                "razorpay_key": RAZORPAY_KEY_ID,
                "amount_inr": round(data['total_amount'], 2),
            }, status=status.HTTP_200_OK)

        except razorpay.errors.RazorpayError as e:
            logging.error(f"Razorpay order creation failed: {e}")
            return Response({"error": "Could not create order"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyPaymentAPIView(APIView):
    def post(self, request):
        data = request.data

        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            logger.warning("⚠️ Missing payment verification parameters")
            return Response(
                {"error": "Missing payment details"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Initialize Razorpay client
            client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

            # Verify Razorpay signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }

            client.utility.verify_payment_signature(params_dict)
            logger.info(f"✅ Payment verified: OrderID={razorpay_order_id}, PaymentID={razorpay_payment_id}")

            # === FETCH ORDER DETAILS FROM RAZORPAY ===
            try:
                order_details = client.order.fetch(razorpay_order_id)
                payment_details = client.payment.fetch(razorpay_payment_id)
                
                # Extract customer details from order notes
                notes = order_details.get('notes', {})
                
                admin_order_details = {
                    'name': notes.get('name', 'N/A'),
                    'email': notes.get('email', 'N/A'),
                    'amount_usd': float(notes.get('amount_usd', 0)),
                    'amount_inr': float(notes.get('amount_inr', 0)),
                    'commission': float(notes.get('commission', 0)),
                    'gst': float(notes.get('gst', 0)),
                    'total_amount': float(notes.get('total_amount', 0))
                }
                
                payment_info = {
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'timestamp': payment_details.get('created_at', datetime.now().timestamp())
                }
                
                logger.info(f"📋 Order details retrieved: {admin_order_details}")
                
            except Exception as e:
                logger.error(f"❌ Failed to fetch order/payment details: {str(e)}")
                # Fallback details if fetch fails
                admin_order_details = {
                    'name': 'N/A',
                    'email': 'N/A',
                    'amount_usd': 0,
                    'amount_inr': 0,
                    'commission': 0,
                    'gst': 0,
                    'total_amount': 0
                }
                payment_info = {
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'timestamp': datetime.now().timestamp()
                }

            # === SEND ADMIN SUCCESS EMAIL ===
            admin_email_sent = send_admin_notification(
                admin_order_details, 
                payment_info, 
                email_type="payment_verified"
            )

            # === SEND USER SUCCESS EMAIL ===
            user_email_sent = send_user_success_email(admin_order_details, payment_info)

            if admin_email_sent:
                logger.info(f"📧 ✅ Admin success email sent for OrderID={razorpay_order_id}")
            else:
                logger.error(f"📧 ❌ Admin success email failed for OrderID={razorpay_order_id}")

            if user_email_sent:
                logger.info(f"📧 ✅ User success email sent for OrderID={razorpay_order_id}")
            else:
                logger.error(f"📧 ❌ User success email failed for OrderID={razorpay_order_id}")

            return Response(
                {
                    "status": "Payment verified successfully",
                    "admin_notified": admin_email_sent,
                    "user_notified": user_email_sent,
                    "order_id": razorpay_order_id,
                    "payment_id": razorpay_payment_id
                },
                status=status.HTTP_200_OK
            )

        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f"❌ Signature verification failed: {str(e)}")
            return Response(
                {"error": "Invalid payment signature"},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"❌ Unexpected error during verification: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )