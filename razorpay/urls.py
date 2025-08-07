from django.urls import path
from .views import ContactFormView

urlpatterns = [
    path('submit/', ContactFormView.as_view(), name='contact-form'),
]
