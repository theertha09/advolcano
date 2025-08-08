import logging
import razorpay
import requests

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# === API KEYS & CONFIG ===
RAZORPAY_KEY_ID = 'rzp_test_tgfXXfzhjjdkYx'
RAZORPAY_KEY_SECRET = '13z5OpJYPLgLhI0CHyMR6Fu9'
ADMIN_EMAIL = "theerthakk467@gmail.com"               # ✅ Set admin recipient
FROM_EMAIL = "noreply@advolcano.io"              # ✅ Must be verified in SendGrid

# === Logging configuration ===
logging.basicConfig(
    filename="payment_logs.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# === Serializers ===
class PaymentSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=15)
    amount_usd = serializers.FloatField(min_value=0.01)
    amount_inr = serializers.FloatField(min_value=0.01)
    commission = serializers.FloatField(min_value=0.0)
    gst = serializers.FloatField(min_value=0.0)
    total_amount = serializers.FloatField(min_value=0.01)

# === Create Payment API ===
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
                    "phone": data['phone_number'],
                    "amount_usd": str(data['amount_usd']),
                    "amount_inr": str(data['amount_inr']),
                    "commission": str(data['commission']),
                    "gst": str(data['gst']),
                    "total_amount": str(data['total_amount']),
                }
            }

            order = client.order.create(data=order_data)

            logging.info(f"Order created: name={data['name']} email={data['email']} "
                         f"phone={data['phone_number']} USD={data['amount_usd']} "
                         f"INR={data['amount_inr']} Commission={data['commission']} "
                         f"GST={data['gst']} Total={data['total_amount']} OrderID={order.get('id')}")

            # === Send Professional Confirmation Email ===
            subject = "Payment Initiated – Order Confirmation"

            email_body = f"""
Dear {data['name']},

Thank you for initiating your payment with us. We’ve successfully created your order with the following details:

--------------------------------------------------------
Payment Summary
--------------------------------------------------------
• Name             : {data['name']}
• Email            : {data['email']}
• Phone Number     : {data['phone_number']}

• Amount (USD)     : ${data['amount_usd']:.2f}
• Amount (INR)     : ₹{data['amount_inr']:.2f}
• Commission Fee   : ₹{data['commission']:.2f}
• GST              : ₹{data['gst']:.2f}
• Total Amount     : ₹{data['total_amount']:.2f}
• Razorpay Order ID: {order.get('id')}
--------------------------------------------------------

What’s Next?
Please proceed to complete your payment using the Razorpay interface. This confirmation ensures your order is recorded and being processed securely.

If you have any questions or concerns, feel free to reach out to us at support@advolcano.io.

Best regards,  
The AdVolcano Payments Team  
noreply@advolcano.io
"""

            message = Mail(
                from_email='noreply@advolcano.io',
                to_emails=data['email'],
                subject=subject,
                plain_text_content=email_body
            )

            try:
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                sg.send(message)
                logging.info(f"Confirmation email sent to {data['email']}")
            except Exception as e:
                logging.error(f"Failed to send email: {e}")

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
            logging.warning("⚠️ Missing payment verification parameters")
            return Response({"error": "Missing payment details"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

            # Verify signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }

            # ✅ Will raise an exception if invalid
            client.utility.verify_payment_signature(params_dict)

            # ✅ If no exception, verification is successful
            logging.info(f"✅ Payment verified: OrderID={razorpay_order_id}, PaymentID={razorpay_payment_id}")

            # ✅ Send email to admin
            subject = "✅ Payment Verified - Razorpay"
            email_body = f"""
Hi Admin,

A new Razorpay payment has been successfully verified.

Details:
- Razorpay Order ID: {razorpay_order_id}
- Razorpay Payment ID: {razorpay_payment_id}
- Status: ✅ VERIFIED

Thanks,
Payment System
"""

            try:
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                message = Mail(
                    from_email=FROM_EMAIL,
                    to_emails=ADMIN_EMAIL,
                    subject=subject,
                    plain_text_content=email_body
                )
                sg.send(message)
                logging.info(f"📧 Admin email sent for OrderID={razorpay_order_id}")
            except Exception as e:
                logging.error(f"❌ Failed to send admin email: {str(e)}")

            return Response({"status": "Payment verified successfully"}, status=status.HTTP_200_OK)

        except razorpay.errors.SignatureVerificationError as e:
            logging.error(f"❌ Signature verification failed: {str(e)}")
            # ❌ No email sent here
            return Response({"error": "Invalid payment signature"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logging.error(f"❌ Unexpected error during verification: {str(e)}")
            # ❌ No email sent here
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
