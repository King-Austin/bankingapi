from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuthViewSet, UserViewSet, BankAccountViewSet, TransactionViewSet,
    BeneficiaryViewSet, CardViewSet, AccountTypeViewSet, TransactionCategoryViewSet,
    health_check
)

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'user', UserViewSet, basename='user')
router.register(r'accounts', BankAccountViewSet, basename='bankaccount')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'beneficiaries', BeneficiaryViewSet, basename='beneficiary')
router.register(r'cards', CardViewSet, basename='card')
router.register(r'account-types', AccountTypeViewSet, basename='accounttype')
router.register(r'transaction-categories', TransactionCategoryViewSet, basename='transactioncategory')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/health/', health_check, name='health_check'),
]
