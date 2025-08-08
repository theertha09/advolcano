from django.urls import path
from .views import CreatePaymentAPIView,VerifyPaymentAPIView

urlpatterns = [
    path('create-payment/', CreatePaymentAPIView.as_view(), name='create-payment'),
    path('payment/verify/', VerifyPaymentAPIView.as_view(), name='verify-payment'),
]
