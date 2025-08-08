from django.urls import path
from .views import CreatePaymentAPIView

urlpatterns = [
    path('create-payment/', CreatePaymentAPIView.as_view(), name='create-payment'),
    # path('verify-payment/', VerifyPaymentAPIView.as_view(), name='verify-payment'),
]
