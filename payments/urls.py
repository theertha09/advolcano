from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Razorpay endpoints
    path('api/payments/', include('payments_razorpay.urls')),

    # Demo request/mail endpoints
    path('api/demo/', include('demo.urls')),
]
