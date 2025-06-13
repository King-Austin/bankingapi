"""
Test cases for Core models
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from decimal import Decimal
from datetime import date, timedelta
from core.models import (
    User, AccountType, BankAccount, TransactionCategory, 
    Transaction, Beneficiary, Card, AuditLog
)

User = get_user_model()


class UserModelTest(TestCase):
    """Test cases for User model"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'phone_number': '08123456789',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123'
        }
    
    def test_create_user(self):
        """Test creating a user"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.phone_number, '08123456789')
        self.assertFalse(user.is_verified)
        self.assertFalse(user.two_factor_enabled)
    
    def test_user_string_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(**self.user_data)
        expected = f"{user.username} - {user.get_full_name()}"
        self.assertEqual(str(user), expected)
    
    def test_unique_email_constraint(self):
        """Test that email must be unique"""
        User.objects.create_user(**self.user_data)
        
        # Try to create another user with same email
        duplicate_data = self.user_data.copy()
        duplicate_data['username'] = 'testuser2'
        duplicate_data['phone_number'] = '08123456790'
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(**duplicate_data)
    
    def test_unique_phone_constraint(self):
        """Test that phone number must be unique"""
        User.objects.create_user(**self.user_data)
        
        # Try to create another user with same phone
        duplicate_data = self.user_data.copy()
        duplicate_data['username'] = 'testuser2'
        duplicate_data['email'] = 'test2@example.com'
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(**duplicate_data)


class AccountTypeModelTest(TestCase):
    """Test cases for AccountType model"""
    
    def setUp(self):
        self.account_type_data = {
            'name': 'Savings',
            'description': 'Regular savings account',
            'minimum_balance': Decimal('1000.00'),
            'interest_rate': Decimal('2.50'),
            'monthly_fee': Decimal('0.00'),
            'transaction_limit_daily': Decimal('50000.00')
        }
    
    def test_create_account_type(self):
        """Test creating an account type"""
        account_type = AccountType.objects.create(**self.account_type_data)
        self.assertEqual(account_type.name, 'Savings')
        self.assertEqual(account_type.minimum_balance, Decimal('1000.00'))
        self.assertTrue(account_type.is_active)
    
    def test_account_type_string_representation(self):
        """Test account type string representation"""
        account_type = AccountType.objects.create(**self.account_type_data)
        self.assertEqual(str(account_type), 'Savings')


class BankAccountModelTest(TestCase):
    """Test cases for BankAccount model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.account_type = AccountType.objects.create(
            name='Savings',
            minimum_balance=Decimal('1000.00')
        )
    
    def test_create_bank_account(self):
        """Test creating a bank account"""
        account = BankAccount.objects.create(
            user=self.user,
            account_type=self.account_type
        )
        self.assertEqual(account.user, self.user)
        self.assertEqual(account.status, 'ACTIVE')
        self.assertEqual(account.balance, Decimal('0.00'))
        self.assertFalse(account.is_primary)
        self.assertIsNotNone(account.account_number)
    
    def test_account_number_generation(self):
        """Test account number is generated from phone number"""
        account = BankAccount.objects.create(
            user=self.user,
            account_type=self.account_type
        )
        # Phone: 08123456789 -> Account: 8123456789 (remove leading 0)
        self.assertEqual(account.account_number, '8123456789')
    
    def test_account_number_generation_with_country_code(self):
        """Test account number generation with country code"""
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            phone_number='+2348123456789',
            password='testpass123'
        )
        account = BankAccount.objects.create(
            user=user,
            account_type=self.account_type
        )
        self.assertEqual(account.account_number, '8123456789')
    
    def test_bank_account_string_representation(self):
        """Test bank account string representation"""
        account = BankAccount.objects.create(
            user=self.user,
            account_type=self.account_type
        )
        expected = f"{self.user.username} - {account.account_number}"
        self.assertEqual(str(account), expected)


class TransactionCategoryModelTest(TestCase):
    """Test cases for TransactionCategory model"""
    
    def test_create_transaction_category(self):
        """Test creating a transaction category"""
        category = TransactionCategory.objects.create(
            name='Transfer',
            description='Money transfer between accounts',
            icon='transfer'
        )
        self.assertEqual(category.name, 'Transfer')
        self.assertTrue(category.is_active)
    
    def test_category_string_representation(self):
        """Test category string representation"""
        category = TransactionCategory.objects.create(name='Transfer')
        self.assertEqual(str(category), 'Transfer')


class TransactionModelTest(TestCase):
    """Test cases for Transaction model"""
    
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
    
    def test_create_transaction(self):
        """Test creating a transaction"""
        transaction = Transaction.objects.create(
            account=self.account,
            transaction_type='DEBIT',
            category=self.category,
            amount=Decimal('1000.00'),
            balance_before=Decimal('10000.00'),
            balance_after=Decimal('9000.00'),
            description='Test transfer'
        )
        self.assertEqual(transaction.account, self.account)
        self.assertEqual(transaction.amount, Decimal('1000.00'))
        self.assertEqual(transaction.status, 'PENDING')
        self.assertIsNotNone(transaction.reference_number)
    
    def test_reference_number_generation(self):
        """Test reference number is automatically generated"""
        transaction = Transaction.objects.create(
            account=self.account,
            transaction_type='CREDIT',
            category=self.category,
            amount=Decimal('500.00'),
            balance_before=Decimal('10000.00'),
            balance_after=Decimal('10500.00'),
            description='Test credit'
        )
        self.assertTrue(transaction.reference_number.startswith('TXN'))
        self.assertEqual(len(transaction.reference_number), 21)  # TXN + 14 digits timestamp + 4 random
    
    def test_transaction_string_representation(self):
        """Test transaction string representation"""
        transaction = Transaction.objects.create(
            account=self.account,
            transaction_type='CREDIT',
            category=self.category,
            amount=Decimal('500.00'),
            balance_before=Decimal('10000.00'),
            balance_after=Decimal('10500.00'),
            description='Test credit'
        )
        expected = f"{transaction.reference_number} - {transaction.amount}"
        self.assertEqual(str(transaction), expected)


class BeneficiaryModelTest(TestCase):
    """Test cases for Beneficiary model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
    
    def test_create_beneficiary(self):
        """Test creating a beneficiary"""
        beneficiary = Beneficiary.objects.create(
            user=self.user,
            account_number='1234567890',
            account_name='John Doe',
            bank_name='SecureCipher Bank',
            nickname='Johnny'
        )
        self.assertEqual(beneficiary.account_number, '1234567890')
        self.assertEqual(beneficiary.account_name, 'John Doe')
        self.assertTrue(beneficiary.is_active)
    
    def test_beneficiary_string_representation(self):
        """Test beneficiary string representation"""
        beneficiary = Beneficiary.objects.create(
            user=self.user,
            account_number='1234567890',
            account_name='John Doe'
        )
        expected = f"{beneficiary.account_name} - {beneficiary.account_number}"
        self.assertEqual(str(beneficiary), expected)


class CardModelTest(TestCase):
    """Test cases for Card model"""
    
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
    
    def test_create_card(self):
        """Test creating a card"""
        card = Card.objects.create(
            account=self.account,
            card_type='DEBIT',
            cardholder_name='Test User',
            expiry_date=date.today() + timedelta(days=365*3)
        )
        self.assertEqual(card.account, self.account)
        self.assertEqual(card.card_type, 'DEBIT')
        self.assertEqual(card.status, 'ACTIVE')
        self.assertIsNotNone(card.card_number)
        self.assertIsNotNone(card.cvv)
        self.assertIsNotNone(card.pin)
    
    def test_card_number_generation(self):
        """Test card number is automatically generated"""
        card = Card.objects.create(
            account=self.account,
            card_type='DEBIT',
            cardholder_name='Test User',
            expiry_date=date.today() + timedelta(days=365*3)
        )
        self.assertTrue(card.card_number.startswith('4'))  # Visa format
        self.assertEqual(len(card.card_number), 16)
        self.assertEqual(len(card.cvv), 3)
        self.assertEqual(len(card.pin), 4)
    
    def test_card_string_representation(self):
        """Test card string representation"""
        card = Card.objects.create(
            account=self.account,
            card_type='DEBIT',
            cardholder_name='Test User',
            expiry_date=date.today() + timedelta(days=365*3)
        )
        expected = f"{card.cardholder_name} - ****{card.card_number[-4:]}"
        self.assertEqual(str(card), expected)


class AuditLogModelTest(TestCase):
    """Test cases for AuditLog model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
    
    def test_create_audit_log(self):
        """Test creating an audit log"""
        log = AuditLog.objects.create(
            user=self.user,
            action_type='LOGIN',
            description='User logged in successfully',
            ip_address='192.168.1.1'
        )
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action_type, 'LOGIN')
        self.assertIsNotNone(log.created_at)
    
    def test_audit_log_string_representation(self):
        """Test audit log string representation"""
        log = AuditLog.objects.create(
            user=self.user,
            action_type='LOGIN',
            description='User logged in successfully'
        )
        expected = f"{log.user} - {log.action_type} - {log.created_at}"
        self.assertEqual(str(log), expected)
