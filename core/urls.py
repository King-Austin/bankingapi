from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuthViewSet, UserViewSet, BankAccountViewSet, TransactionViewSet,
    health_check
)

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'user', UserViewSet, basename='user')
router.register(r'accounts', BankAccountViewSet, basename='bankaccount')
router.register(r'transactions', TransactionViewSet, basename='transaction')


urlpatterns = [
    path('', include(router.urls)),
    path('health/', health_check, name='health_check'),
]
