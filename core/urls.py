from django.urls import path
from .views import (
    RegisterView, LoginView, ValidateAccountView, TransferView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('validate_account/', ValidateAccountView.as_view(), name='validate_account'),
    path('transfer/', TransferView.as_view(), name='transfer'),
]