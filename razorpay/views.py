import os
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers

# ✅ Serializer with `usd`
class ContactFormSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=15)
    usd = serializers.DecimalField(max_digits=10, decimal_places=2)

# ✅ API View with UUID logging
class ContactFormView(APIView):
    def post(self, request):
        serializer = ContactFormSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            unique_id = str(uuid.uuid4())  # 🔑 generate unique UUID

            log_entry = (
                f"UUID: {unique_id}, "
                f"Name: {data['name']}, "
                f"Email: {data['email']}, "
                f"Phone: {data['phone']}, "
                f"USD: {data['usd']}\n"
            )

            # Save to file in the razorpay app folder
            log_file = os.path.join(os.path.dirname(__file__), 'form_logs.txt')
            with open(log_file, 'a') as f:
                f.write(log_entry)

            return Response({
                "message": "Data saved to log file.",
                "uuid": unique_id
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        log_file = os.path.join(os.path.dirname(__file__), 'form_logs.txt')
        if not os.path.exists(log_file):
            return Response({"message": "Log file not found."}, status=status.HTTP_404_NOT_FOUND)

        with open(log_file, 'r') as f:
            logs = f.readlines()

        return Response({"logs": logs}, status=status.HTTP_200_OK)
