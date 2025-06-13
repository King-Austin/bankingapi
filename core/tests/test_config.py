"""
Test configuration and utilities
"""
import os
from django.test import TestCase
from django.conf import settings
from django.core.management import call_command
from django.test.utils import override_settings


# Test database configuration
TEST_DATABASE_CONFIG = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Use in-memory database for faster tests
    }
}


class BaseTestCase(TestCase):
    """Base test case with common setup and utilities"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create necessary test data that should be available for all tests
        cls.create_test_categories()
        cls.create_test_account_types()
    
    @classmethod
    def create_test_categories(cls):
        """Create basic transaction categories for tests"""
        from core.models import TransactionCategory
        
        categories = [
            {'name': 'Transfer', 'description': 'Money transfer between accounts'},
            {'name': 'Deposit', 'description': 'Money deposit'},
            {'name': 'Withdrawal', 'description': 'Money withdrawal'},
            {'name': 'Payment', 'description': 'Bill payment'},
        ]
        
        for cat_data in categories:
            TransactionCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
    
    @classmethod
    def create_test_account_types(cls):
        """Create basic account types for tests"""
        from core.models import AccountType
        from decimal import Decimal
        
        account_types = [
            {
                'name': 'Savings',
                'description': 'Regular savings account',
                'minimum_balance': Decimal('1000.00'),
                'interest_rate': Decimal('2.50'),
                'transaction_limit_daily': Decimal('50000.00')
            },
            {
                'name': 'Current',
                'description': 'Current account for daily transactions',
                'minimum_balance': Decimal('0.00'),
                'interest_rate': Decimal('0.00'),
                'transaction_limit_daily': Decimal('100000.00')
            }
        ]
        
        for acc_data in account_types:
            AccountType.objects.get_or_create(
                name=acc_data['name'],
                defaults=acc_data
            )
    
    def setUp(self):
        """Set up for each test method"""
        super().setUp()
        # Clear any cached data
        from django.core.cache import cache
        cache.clear()
    
    def tearDown(self):
        """Clean up after each test method"""
        super().tearDown()
        # Any additional cleanup can go here


class APITestMixin:
    """Mixin for API tests with common authentication helpers"""
    
    def create_authenticated_client(self, user=None):
        """Create an authenticated API client"""
        from rest_framework.test import APIClient
        from rest_framework.authtoken.models import Token
        from django.contrib.auth import get_user_model
        
        if user is None:
            User = get_user_model()
            user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                phone_number='08123456789',
                password='testpass123'
            )
        
        token, created = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        
        return client, user, token
    
    def assert_api_error(self, response, status_code, error_key=None):
        """Assert API error response"""
        self.assertEqual(response.status_code, status_code)
        if error_key:
            self.assertIn(error_key, response.data)
    
    def assert_api_success(self, response, status_code=200):
        """Assert API success response"""
        self.assertEqual(response.status_code, status_code)


# Test settings overrides
TEST_SETTINGS_OVERRIDES = {
    'DATABASES': TEST_DATABASE_CONFIG,
    'PASSWORD_HASHERS': [
        'django.contrib.auth.hashers.MD5PasswordHasher',  # Faster for tests
    ],
    'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
    'CACHES': {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
    'CELERY_TASK_ALWAYS_EAGER': True,  # Run Celery tasks synchronously in tests
    'MEDIA_ROOT': '/tmp/test_media/',
    'STATIC_ROOT': '/tmp/test_static/',
}


def run_test_coverage():
    """Run tests with coverage report"""
    import coverage
    
    cov = coverage.Coverage()
    cov.start()
    
    # Run tests
    from django.test.utils import get_runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2)
    failures = test_runner.run_tests(['core'])
    
    cov.stop()
    cov.save()
    
    # Generate coverage report
    print("\n" + "="*50)
    print("COVERAGE REPORT")
    print("="*50)
    cov.report()
    
    # Generate HTML coverage report
    cov.html_report(directory='htmlcov')
    print(f"\nHTML coverage report generated in 'htmlcov' directory")
    
    return failures


class MockDataMixin:
    """Mixin for creating mock test data"""
    
    def create_mock_users(self, count=5):
        """Create multiple mock users"""
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        users = []
        
        for i in range(count):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                phone_number=f'0812345678{i}',
                first_name=f'User{i}',
                last_name='Test',
                password='testpass123'
            )
            users.append(user)
        
        return users
    
    def create_mock_accounts(self, users=None, count=None):
        """Create mock bank accounts"""
        from core.models import BankAccount, AccountType
        from decimal import Decimal
        
        if users is None:
            if count is None:
                count = 3
            users = self.create_mock_users(count)
        
        account_type = AccountType.objects.first()
        accounts = []
        
        for user in users:
            account = BankAccount.objects.create(
                user=user,
                account_type=account_type,
                balance=Decimal('10000.00')
            )
            accounts.append(account)
        
        return accounts
    
    def create_mock_transactions(self, accounts=None, count=10):
        """Create mock transactions"""
        from core.models import Transaction, TransactionCategory
        from decimal import Decimal
        import random
        
        if accounts is None:
            accounts = self.create_mock_accounts()
        
        category = TransactionCategory.objects.first()
        transactions = []
        
        for i in range(count):
            account = random.choice(accounts)
            transaction = Transaction.objects.create(
                account=account,
                transaction_type=random.choice(['CREDIT', 'DEBIT']),
                category=category,
                amount=Decimal(random.randint(100, 5000)),
                balance_before=Decimal('10000.00'),
                balance_after=Decimal('9000.00'),
                description=f'Mock transaction {i}'
            )
            transactions.append(transaction)
        
        return transactions


if __name__ == '__main__':
    run_test_coverage()
