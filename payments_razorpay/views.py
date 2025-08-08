import logging
import razorpay
import requests

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# === API KEYS & CONFIG ===
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

        total_amount_paise = int(round(data['total_amount'] * 100))  # INR → paise

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
                    "total_amount": str(data['total_amount'])
                }
            }
            order = client.order.create(data=order_data)

            logging.info(f"Order created: name={data['name']} email={data['email']} "
                         f"phone={data['phone_number']} USD={data['amount_usd']} "
                         f"INR={data['amount_inr']} Commission={data['commission']} "
                         f"GST={data['gst']} Total={data['total_amount']} OrderID={order.get('id')}")

            # Send confirmation email
            subject = "Payment Initiated - Order Confirmation"
            email_body = f"""
Hi {data['name']},

Your payment has been initiated successfully.

Details:
- Name: {data['name']}
- Email: {data['email']}
- Phone: {data['phone_number']}
- Amount (USD): ${data['amount_usd']:.2f}
- Amount (INR): ₹{data['amount_inr']:.2f}
- Commission Fee: ₹{data['commission']:.2f}
- GST: ₹{data['gst']:.2f}
- Total Amount: ₹{data['total_amount']:.2f}
- Order ID: {order.get('id')}

Thank you,
Your Payment Team
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
            }, status=200)

        except razorpay.errors.RazorpayError as e:
            logging.error(f"Razorpay order creation failed: {e}")
            return Response({"error": "Could not create order"}, status=500)
