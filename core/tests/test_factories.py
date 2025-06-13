"""
Test data factories for creating test objects
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
import random
from core.models import (
    AccountType, BankAccount, TransactionCategory, 
    Transaction, Beneficiary, Card, AuditLog
)

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances"""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    phone_number = factory.Sequence(lambda n: f'08123456{n:03d}')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_verified = False
    two_factor_enabled = False


class AccountTypeFactory(DjangoModelFactory):
    """Factory for creating AccountType instances"""
    
    class Meta:
        model = AccountType
    
    name = factory.Iterator(['Savings', 'Current', 'Business', 'Premium'])
    description = factory.Faker('text', max_nb_chars=100)
    minimum_balance = factory.LazyFunction(lambda: Decimal(random.randint(0, 5000)))
    interest_rate = factory.LazyFunction(lambda: Decimal(random.uniform(0, 10)))
    monthly_fee = factory.LazyFunction(lambda: Decimal(random.randint(0, 100)))
    transaction_limit_daily = factory.LazyFunction(lambda: Decimal(random.randint(10000, 100000)))
    is_active = True


class BankAccountFactory(DjangoModelFactory):
    """Factory for creating BankAccount instances"""
    
    class Meta:
        model = BankAccount
    
    user = factory.SubFactory(UserFactory)
    account_type = factory.SubFactory(AccountTypeFactory)
    balance = factory.LazyFunction(lambda: Decimal(random.randint(0, 100000)))
    available_balance = factory.LazyAttribute(lambda obj: obj.balance)
    status = 'ACTIVE'
    is_primary = False


class TransactionCategoryFactory(DjangoModelFactory):
    """Factory for creating TransactionCategory instances"""
    
    class Meta:
        model = TransactionCategory
    
    name = factory.Iterator(['Transfer', 'Deposit', 'Withdrawal', 'Payment', 'Refund'])
    description = factory.Faker('text', max_nb_chars=100)
    icon = factory.Iterator(['transfer', 'deposit', 'withdrawal', 'payment', 'refund'])
    is_active = True


class TransactionFactory(DjangoModelFactory):
    """Factory for creating Transaction instances"""
    
    class Meta:
        model = Transaction
    
    account = factory.SubFactory(BankAccountFactory)
    transaction_type = factory.Iterator(['CREDIT', 'DEBIT'])
    category = factory.SubFactory(TransactionCategoryFactory)
    amount = factory.LazyFunction(lambda: Decimal(random.randint(100, 10000)))
    balance_before = factory.LazyFunction(lambda: Decimal(random.randint(0, 50000)))
    balance_after = factory.LazyAttribute(
        lambda obj: obj.balance_before + obj.amount if obj.transaction_type == 'CREDIT' 
        else obj.balance_before - obj.amount
    )
    description = factory.Faker('sentence', nb_words=4)
    status = 'COMPLETED'


class BeneficiaryFactory(DjangoModelFactory):
    """Factory for creating Beneficiary instances"""
    
    class Meta:
        model = Beneficiary
    
    user = factory.SubFactory(UserFactory)
    account_number = factory.Sequence(lambda n: f'81234567{n:02d}')
    account_name = factory.Faker('name')
    bank_name = 'SecureCipher Bank'
    nickname = factory.Faker('first_name')
    is_active = True


class CardFactory(DjangoModelFactory):
    """Factory for creating Card instances"""
    
    class Meta:
        model = Card
    
    account = factory.SubFactory(BankAccountFactory)
    card_type = factory.Iterator(['DEBIT', 'CREDIT'])
    cardholder_name = factory.LazyAttribute(lambda obj: obj.account.user.get_full_name())
    expiry_date = factory.LazyFunction(lambda: date.today() + timedelta(days=365*3))
    status = 'ACTIVE'
    daily_limit = factory.LazyFunction(lambda: Decimal(random.randint(10000, 100000)))
    is_international = False


class AuditLogFactory(DjangoModelFactory):
    """Factory for creating AuditLog instances"""
    
    class Meta:
        model = AuditLog
    
    user = factory.SubFactory(UserFactory)
    action_type = factory.Iterator(['LOGIN', 'LOGOUT', 'TRANSACTION', 'ACCOUNT_UPDATE', 'PASSWORD_CHANGE'])
    description = factory.Faker('sentence', nb_words=6)
    ip_address = factory.Faker('ipv4')
    user_agent = factory.Faker('user_agent')


class TestDataMixin:
    """Mixin to provide common test data creation methods"""
    
    @classmethod
    def create_test_user(cls, **kwargs):
        """Create a test user with default or custom attributes"""
        defaults = {
            'username': 'testuser',
            'email': 'test@example.com',
            'phone_number': '08123456789',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123'
        }
        defaults.update(kwargs)
        return User.objects.create_user(**defaults)
    
    @classmethod
    def create_test_account(cls, user=None, **kwargs):
        """Create a test bank account"""
        if user is None:
            user = cls.create_test_user()
        
        account_type, _ = AccountType.objects.get_or_create(
            name='Savings',
            defaults={
                'minimum_balance': Decimal('1000.00'),
                'transaction_limit_daily': Decimal('50000.00')
            }
        )
        
        defaults = {
            'user': user,
            'account_type': account_type,
            'balance': Decimal('10000.00')
        }
        defaults.update(kwargs)
        return BankAccount.objects.create(**defaults)
    
    @classmethod
    def create_test_transaction(cls, account=None, **kwargs):
        """Create a test transaction"""
        if account is None:
            account = cls.create_test_account()
        
        category, _ = TransactionCategory.objects.get_or_create(
            name='Transfer',
            defaults={'description': 'Money transfer'}
        )
        
        defaults = {
            'account': account,
            'transaction_type': 'DEBIT',
            'category': category,
            'amount': Decimal('1000.00'),
            'balance_before': Decimal('10000.00'),
            'balance_after': Decimal('9000.00'),
            'description': 'Test transaction'
        }
        defaults.update(kwargs)
        return Transaction.objects.create(**defaults)
    
    @classmethod
    def create_test_beneficiary(cls, user=None, **kwargs):
        """Create a test beneficiary"""
        if user is None:
            user = cls.create_test_user()
        
        defaults = {
            'user': user,
            'account_number': '1234567890',
            'account_name': 'John Doe',
            'bank_name': 'SecureCipher Bank'
        }
        defaults.update(kwargs)
        return Beneficiary.objects.create(**defaults)
    
    @classmethod
    def create_test_card(cls, account=None, **kwargs):
        """Create a test card"""
        if account is None:
            account = cls.create_test_account()
        
        defaults = {
            'account': account,
            'card_type': 'DEBIT',
            'cardholder_name': account.user.get_full_name(),
            'expiry_date': date.today() + timedelta(days=365*3)
        }
        defaults.update(kwargs)
        return Card.objects.create(**defaults)
