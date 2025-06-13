"""
Test cases for Core serializers
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from decimal import Decimal
from datetime import date, timedelta
from core.models import (
    AccountType, BankAccount, TransactionCategory, 
    Transaction, Beneficiary, Card
)
from core.serializers import (
    UserSerializer, UserRegistrationSerializer, BankAccountSerializer,
    TransactionSerializer, BeneficiarySerializer, CardSerializer,
    TransferSerializer, AccountValidationSerializer
)

User = get_user_model()


class UserSerializerTest(TestCase):
    """Test cases for User serializers"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'phone_number': '08123456789',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123'
        }
        self.user = User.objects.create_user(**self.user_data)
    
    def test_user_serializer(self):
        """Test UserSerializer serialization"""
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['phone_number'], '08123456789')
        self.assertNotIn('password', data)  # Password should not be included
    
    def test_user_registration_serializer_valid(self):
        """Test UserRegistrationSerializer with valid data"""
        registration_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'phone_number': '08123456790',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123'
        }
        
        serializer = UserRegistrationSerializer(data=registration_data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'new@example.com')
        self.assertTrue(user.check_password('newpass123'))
    
    def test_user_registration_serializer_duplicate_email(self):
        """Test UserRegistrationSerializer with duplicate email"""
        registration_data = {
            'username': 'newuser',
            'email': 'test@example.com',  # Same as existing user
            'phone_number': '08123456790',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123'
        }
        
        serializer = UserRegistrationSerializer(data=registration_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
    
    def test_user_registration_serializer_duplicate_phone(self):
        """Test UserRegistrationSerializer with duplicate phone"""
        registration_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'phone_number': '08123456789',  # Same as existing user
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpass123'
        }
        
        serializer = UserRegistrationSerializer(data=registration_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone_number', serializer.errors)


class BankAccountSerializerTest(TestCase):
    """Test cases for BankAccount serializer"""
    
    def setUp(self):
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
    
    def test_bank_account_serializer(self):
        """Test BankAccount serialization"""
        serializer = BankAccountSerializer(self.account)
        data = serializer.data
        
        self.assertEqual(data['account_number'], self.account.account_number)
        self.assertEqual(data['balance'], '10000.00')
        self.assertEqual(data['status'], 'ACTIVE')
        self.assertIn('account_type', data)


class TransactionSerializerTest(TestCase):
    """Test cases for Transaction serializer"""
    
    def setUp(self):
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
        self.category = TransactionCategory.objects.create(name='Transfer')
        self.transaction = Transaction.objects.create(
            account=self.account,
            transaction_type='DEBIT',
            category=self.category,
            amount=Decimal('1000.00'),
            balance_before=Decimal('10000.00'),
            balance_after=Decimal('9000.00'),
            description='Test transfer'
        )
    
    def test_transaction_serializer(self):
        """Test Transaction serialization"""
        serializer = TransactionSerializer(self.transaction)
        data = serializer.data
        
        self.assertEqual(data['amount'], '1000.00')
        self.assertEqual(data['transaction_type'], 'DEBIT')
        self.assertEqual(data['description'], 'Test transfer')
        self.assertIn('reference_number', data)
        self.assertIn('created_at', data)


class BeneficiarySerializerTest(TestCase):
    """Test cases for Beneficiary serializer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.beneficiary_data = {
            'account_number': '1234567890',
            'account_name': 'John Doe',
            'bank_name': 'SecureCipher Bank',
            'nickname': 'Johnny'
        }
    
    def test_beneficiary_serializer_valid(self):
        """Test Beneficiary serializer with valid data"""
        serializer = BeneficiarySerializer(data=self.beneficiary_data)
        self.assertTrue(serializer.is_valid())
        
        beneficiary = serializer.save(user=self.user)
        self.assertEqual(beneficiary.account_name, 'John Doe')
        self.assertEqual(beneficiary.account_number, '1234567890')
    
    def test_beneficiary_serializer_invalid_account_number(self):
        """Test Beneficiary serializer with invalid account number"""
        invalid_data = self.beneficiary_data.copy()
        invalid_data['account_number'] = '123'  # Too short
        
        serializer = BeneficiarySerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())


class CardSerializerTest(TestCase):
    """Test cases for Card serializer"""
    
    def setUp(self):
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
        self.card = Card.objects.create(
            account=self.account,
            card_type='DEBIT',
            cardholder_name='Test User',
            expiry_date=date.today() + timedelta(days=365*3)
        )
    
    def test_card_serializer(self):
        """Test Card serialization"""
        serializer = CardSerializer(self.card)
        data = serializer.data
        
        self.assertEqual(data['card_type'], 'DEBIT')
        self.assertEqual(data['cardholder_name'], 'Test User')
        self.assertIn('masked_card_number', data)
        self.assertNotIn('card_number', data)  # Full card number should not be exposed
        self.assertNotIn('cvv', data)  # CVV should not be exposed
        self.assertNotIn('pin', data)  # PIN should not be exposed


class TransferSerializerTest(TestCase):
    """Test cases for Transfer serializer"""
    
    def setUp(self):
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
    
    def test_transfer_serializer_valid(self):
        """Test Transfer serializer with valid data"""
        transfer_data = {
            'recipient_account_number': self.recipient_account.account_number,
            'amount': '1000.00',
            'description': 'Test transfer'
        }
        
        serializer = TransferSerializer(data=transfer_data)
        serializer.context = {'sender_account': self.sender_account}
        self.assertTrue(serializer.is_valid())
    
    def test_transfer_serializer_invalid_amount(self):
        """Test Transfer serializer with invalid amount"""
        transfer_data = {
            'recipient_account_number': self.recipient_account.account_number,
            'amount': '0.00',  # Invalid amount
            'description': 'Test transfer'
        }
        
        serializer = TransferSerializer(data=transfer_data)
        serializer.context = {'sender_account': self.sender_account}
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)
    
    def test_transfer_serializer_insufficient_funds(self):
        """Test Transfer serializer with insufficient funds"""
        transfer_data = {
            'recipient_account_number': self.recipient_account.account_number,
            'amount': '15000.00',  # More than balance
            'description': 'Test transfer'
        }
        
        serializer = TransferSerializer(data=transfer_data)
        serializer.context = {'sender_account': self.sender_account}
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)


class AccountValidationSerializerTest(TestCase):
    """Test cases for Account Validation serializer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.account_type = AccountType.objects.create(name='Savings')
        self.account = BankAccount.objects.create(
            user=self.user,
            account_type=self.account_type
        )
    
    def test_account_validation_serializer_valid(self):
        """Test Account Validation serializer with valid account number"""
        validation_data = {
            'account_number': self.account.account_number
        }
        
        serializer = AccountValidationSerializer(data=validation_data)
        self.assertTrue(serializer.is_valid())
    
    def test_account_validation_serializer_invalid_length(self):
        """Test Account Validation serializer with invalid account number length"""
        validation_data = {
            'account_number': '123'  # Too short
        }
        
        serializer = AccountValidationSerializer(data=validation_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('account_number', serializer.errors)
