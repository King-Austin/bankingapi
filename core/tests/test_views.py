"""
Test cases for Core views and API endpoints
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from decimal import Decimal
from core.models import (
    AccountType, BankAccount, TransactionCategory, 
    Transaction, Beneficiary, Card
)

User = get_user_model()


class AuthenticationViewTest(APITestCase):
    """Test cases for authentication endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'phone_number': '08123456789',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123'
        }
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        url = reverse('register')
        response = self.client.post(url, self.user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        
        # Check user was created
        user = User.objects.get(username='testuser')
        self.assertEqual(user.email, 'test@example.com')
        
        # Check bank account was created with demo funds
        account = BankAccount.objects.get(user=user)
        self.assertEqual(account.balance, Decimal('50000.00'))
        self.assertEqual(account.account_number, '8123456789')  # Phone without leading 0
    
    def test_user_login(self):
        """Test user login endpoint"""
        # Create user first
        user = User.objects.create_user(**self.user_data)
        
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        url = reverse('login')
        response = self.client.post(url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        login_data = {
            'username': 'nonexistent',
            'password': 'wrongpass'
        }
        
        url = reverse('login')
        response = self.client.post(url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_profile(self):
        """Test user profile endpoint"""
        user = User.objects.create_user(**self.user_data)
        token = Token.objects.create(user=user)
        
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        
        url = reverse('user-profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')


class BankAccountViewTest(APITestCase):
    """Test cases for bank account endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.account_type = AccountType.objects.create(name='Savings')
        self.account = BankAccount.objects.create(
            user=self.user,
            account_type=self.account_type,
            balance=Decimal('10000.00')
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
    
    def test_list_accounts(self):
        """Test listing user's bank accounts"""
        url = reverse('accounts')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['balance'], '10000.00')
    
    def test_account_detail(self):
        """Test getting account details"""
        url = reverse('account-detail', kwargs={'account_id': self.account.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['balance'], '10000.00')
    
    def test_account_validation(self):
        """Test account number validation endpoint"""
        url = reverse('validate-account')
        data = {'account_number': self.account.account_number}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['exists'])
        self.assertEqual(response.data['account_name'], self.user.get_full_name())
    
    def test_invalid_account_validation(self):
        """Test validation of non-existent account"""
        url = reverse('validate-account')
        data = {'account_number': '9999999999'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['exists'])


class TransactionViewTest(APITestCase):
    """Test cases for transaction endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.recipient = User.objects.create_user(
            username='recipient',
            email='recipient@example.com',
            phone_number='08123456790',
            password='testpass123'
        )
        
        self.account_type = AccountType.objects.create(name='Savings')
        self.sender_account = BankAccount.objects.create(
            user=self.user,
            account_type=self.account_type,
            balance=Decimal('10000.00')
        )
        self.recipient_account = BankAccount.objects.create(
            user=self.recipient,
            account_type=self.account_type,
            balance=Decimal('5000.00')
        )
        
        self.category = TransactionCategory.objects.create(name='Transfer')
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
    
    def test_list_transactions(self):
        """Test listing user's transactions"""
        # Create a transaction
        Transaction.objects.create(
            account=self.sender_account,
            transaction_type='DEBIT',
            category=self.category,
            amount=Decimal('1000.00'),
            balance_before=Decimal('10000.00'),
            balance_after=Decimal('9000.00'),
            description='Test transfer'
        )
        
        url = reverse('transactions')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_transfer_money(self):
        """Test money transfer between accounts"""
        url = reverse('transfer')
        data = {
            'recipient_account_number': self.recipient_account.account_number,
            'amount': '1000.00',
            'description': 'Test transfer'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check balances updated
        self.sender_account.refresh_from_db()
        self.recipient_account.refresh_from_db()
        self.assertEqual(self.sender_account.balance, Decimal('9000.00'))
        self.assertEqual(self.recipient_account.balance, Decimal('6000.00'))
    
    def test_transfer_insufficient_funds(self):
        """Test transfer with insufficient funds"""
        url = reverse('transfer')
        data = {
            'recipient_account_number': self.recipient_account.account_number,
            'amount': '15000.00',  # More than balance
            'description': 'Test transfer'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_transfer_to_invalid_account(self):
        """Test transfer to non-existent account"""
        url = reverse('transfer')
        data = {
            'recipient_account_number': '9999999999',
            'amount': '1000.00',
            'description': 'Test transfer'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BeneficiaryViewTest(APITestCase):
    """Test cases for beneficiary endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
    
    def test_list_beneficiaries(self):
        """Test listing user's beneficiaries"""
        Beneficiary.objects.create(
            user=self.user,
            account_number='1234567890',
            account_name='John Doe',
            nickname='Johnny'
        )
        
        url = reverse('beneficiaries')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['account_name'], 'John Doe')
    
    def test_create_beneficiary(self):
        """Test creating a new beneficiary"""
        url = reverse('beneficiaries')
        data = {
            'account_number': '1234567890',
            'account_name': 'Jane Doe',
            'bank_name': 'SecureCipher Bank',
            'nickname': 'Jane'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['account_name'], 'Jane Doe')


class CardViewTest(APITestCase):
    """Test cases for card endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.account_type = AccountType.objects.create(name='Savings')
        self.account = BankAccount.objects.create(
            user=self.user,
            account_type=self.account_type,
            balance=Decimal('10000.00')
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
    
    def test_list_cards(self):
        """Test listing user's cards"""
        from datetime import date, timedelta
        
        Card.objects.create(
            account=self.account,
            card_type='DEBIT',
            cardholder_name='Test User',
            expiry_date=date.today() + timedelta(days=365*3)
        )
        
        url = reverse('cards')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['card_type'], 'DEBIT')


class HealthCheckViewTest(APITestCase):
    """Test cases for health check endpoint"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        url = reverse('health')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')


class UnauthorizedAccessTest(APITestCase):
    """Test cases for unauthorized access"""
    
    def test_unauthorized_access_to_protected_endpoints(self):
        """Test that protected endpoints require authentication"""
        protected_urls = [
            reverse('accounts'),
            reverse('transactions'),
            reverse('beneficiaries'),
            reverse('cards'),
            reverse('user-profile'),
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
