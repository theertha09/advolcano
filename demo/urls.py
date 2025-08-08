from django.urls import path
from .views import RequestDemoAPIView

urlpatterns = [
    path('request-demo/', RequestDemoAPIView.as_view(), name='request_demo'),
]
