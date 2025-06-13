"""
Test cases for Core admin functionality
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from decimal import Decimal
from datetime import date, timedelta
from core.models import (
    AccountType, BankAccount, TransactionCategory, 
    Transaction, Beneficiary, Card, AuditLog
)
from core.admin import (
    CustomUserAdmin, AccountTypeAdmin, BankAccountAdmin,
    TransactionCategoryAdmin, TransactionAdmin, BeneficiaryAdmin,
    CardAdmin, AuditLogAdmin
)

User = get_user_model()


class AdminTestCase(TestCase):
    """Base test case for admin tests"""
    
    def setUp(self):
        self.site = AdminSite()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            phone_number='08123456788',
            password='adminpass123'
        )
        self.client = Client()
        self.client.force_login(self.admin_user)


class CustomUserAdminTest(AdminTestCase):
    """Test cases for Custom User Admin"""
    
    def setUp(self):
        super().setUp()
        self.user_admin = CustomUserAdmin(User, self.site)
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
    
    def test_user_admin_list_display(self):
        """Test user admin list display fields"""
        expected_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'is_verified', 'is_staff')
        self.assertEqual(self.user_admin.list_display, expected_fields)
    
    def test_user_admin_list_filter(self):
        """Test user admin list filter fields"""
        expected_filters = ('is_staff', 'is_superuser', 'is_active', 'is_verified', 'date_joined')
        self.assertEqual(self.user_admin.list_filter, expected_filters)
    
    def test_user_admin_search_fields(self):
        """Test user admin search fields"""
        expected_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')
        self.assertEqual(self.user_admin.search_fields, expected_fields)
    
    def test_user_admin_changelist_view(self):
        """Test user admin changelist view"""
        url = reverse('admin:core_user_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')


class AccountTypeAdminTest(AdminTestCase):
    """Test cases for Account Type Admin"""
    
    def setUp(self):
        super().setUp()
        self.account_type_admin = AccountTypeAdmin(AccountType, self.site)
        self.account_type = AccountType.objects.create(
            name='Savings',
            description='Regular savings account',
            minimum_balance=Decimal('1000.00'),
            interest_rate=Decimal('2.50')
        )
    
    def test_account_type_admin_list_display(self):
        """Test account type admin list display fields"""
        expected_fields = ('name', 'minimum_balance', 'interest_rate', 'monthly_fee', 'transaction_limit_daily', 'is_active')
        self.assertEqual(self.account_type_admin.list_display, expected_fields)
    
    def test_account_type_admin_changelist_view(self):
        """Test account type admin changelist view"""
        url = reverse('admin:core_accounttype_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Savings')


class BankAccountAdminTest(AdminTestCase):
    """Test cases for Bank Account Admin"""
    
    def setUp(self):
        super().setUp()
        self.bank_account_admin = BankAccountAdmin(BankAccount, self.site)
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.account_type = AccountType.objects.create(name='Savings')
        self.bank_account = BankAccount.objects.create(
            user=self.test_user,
            account_type=self.account_type,
            balance=Decimal('10000.00')
        )
    
    def test_bank_account_admin_list_display(self):
        """Test bank account admin list display fields"""
        expected_fields = ('account_number', 'user', 'account_type', 'balance', 'status', 'is_primary', 'created_at')
        self.assertEqual(self.bank_account_admin.list_display, expected_fields)
    
    def test_bank_account_admin_readonly_fields(self):
        """Test bank account admin readonly fields"""
        expected_fields = ('id', 'account_number', 'created_at', 'updated_at')
        self.assertEqual(self.bank_account_admin.readonly_fields, expected_fields)
    
    def test_bank_account_admin_changelist_view(self):
        """Test bank account admin changelist view"""
        url = reverse('admin:core_bankaccount_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.bank_account.account_number)


class TransactionAdminTest(AdminTestCase):
    """Test cases for Transaction Admin"""
    
    def setUp(self):
        super().setUp()
        self.transaction_admin = TransactionAdmin(Transaction, self.site)
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.account_type = AccountType.objects.create(name='Savings')
        self.bank_account = BankAccount.objects.create(
            user=self.test_user,
            account_type=self.account_type,
            balance=Decimal('10000.00')
        )
        self.category = TransactionCategory.objects.create(name='Transfer')
        self.transaction = Transaction.objects.create(
            account=self.bank_account,
            transaction_type='DEBIT',
            category=self.category,
            amount=Decimal('1000.00'),
            balance_before=Decimal('10000.00'),
            balance_after=Decimal('9000.00'),
            description='Test transfer'
        )
    
    def test_transaction_admin_list_display(self):
        """Test transaction admin list display fields"""
        expected_fields = ('reference_number', 'account', 'transaction_type', 'amount', 'status', 'created_at')
        self.assertEqual(self.transaction_admin.list_display, expected_fields)
    
    def test_transaction_admin_readonly_fields(self):
        """Test transaction admin readonly fields"""
        expected_fields = ('id', 'reference_number', 'created_at', 'updated_at')
        self.assertEqual(self.transaction_admin.readonly_fields, expected_fields)
    
    def test_transaction_admin_changelist_view(self):
        """Test transaction admin changelist view"""
        url = reverse('admin:core_transaction_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.transaction.reference_number)


class BeneficiaryAdminTest(AdminTestCase):
    """Test cases for Beneficiary Admin"""
    
    def setUp(self):
        super().setUp()
        self.beneficiary_admin = BeneficiaryAdmin(Beneficiary, self.site)
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.beneficiary = Beneficiary.objects.create(
            user=self.test_user,
            account_number='1234567890',
            account_name='John Doe',
            bank_name='SecureCipher Bank'
        )
    
    def test_beneficiary_admin_list_display(self):
        """Test beneficiary admin list display fields"""
        expected_fields = ('account_name', 'user', 'account_number', 'bank_name', 'is_active', 'created_at')
        self.assertEqual(self.beneficiary_admin.list_display, expected_fields)
    
    def test_beneficiary_admin_changelist_view(self):
        """Test beneficiary admin changelist view"""
        url = reverse('admin:core_beneficiary_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')


class CardAdminTest(AdminTestCase):
    """Test cases for Card Admin"""
    
    def setUp(self):
        super().setUp()
        self.card_admin = CardAdmin(Card, self.site)
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.account_type = AccountType.objects.create(name='Savings')
        self.bank_account = BankAccount.objects.create(
            user=self.test_user,
            account_type=self.account_type
        )
        self.card = Card.objects.create(
            account=self.bank_account,
            card_type='DEBIT',
            cardholder_name='Test User',
            expiry_date=date.today() + timedelta(days=365*3)
        )
    
    def test_card_admin_list_display(self):
        """Test card admin list display fields"""
        expected_fields = ('masked_card_number', 'cardholder_name', 'card_type', 'status', 'expiry_date', 'daily_limit')
        self.assertEqual(self.card_admin.list_display, expected_fields)
    
    def test_card_admin_readonly_fields(self):
        """Test card admin readonly fields"""
        expected_fields = ('id', 'card_number', 'created_at', 'updated_at')
        self.assertEqual(self.card_admin.readonly_fields, expected_fields)
    
    def test_card_admin_changelist_view(self):
        """Test card admin changelist view"""
        url = reverse('admin:core_card_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test User')


class AuditLogAdminTest(AdminTestCase):
    """Test cases for Audit Log Admin"""
    
    def setUp(self):
        super().setUp()
        self.audit_log_admin = AuditLogAdmin(AuditLog, self.site)
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='08123456789',
            password='testpass123'
        )
        self.audit_log = AuditLog.objects.create(
            user=self.test_user,
            action_type='LOGIN',
            description='User logged in successfully',
            ip_address='192.168.1.1'
        )
    
    def test_audit_log_admin_list_display(self):
        """Test audit log admin list display fields"""
        expected_fields = ('user', 'action_type', 'description', 'ip_address', 'created_at')
        self.assertEqual(self.audit_log_admin.list_display, expected_fields)
    
    def test_audit_log_admin_permissions(self):
        """Test audit log admin permissions"""
        # Audit logs should not be manually created or modified
        self.assertFalse(self.audit_log_admin.has_add_permission(None))
        self.assertFalse(self.audit_log_admin.has_change_permission(None))
    
    def test_audit_log_admin_changelist_view(self):
        """Test audit log admin changelist view"""
        url = reverse('admin:core_auditlog_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'LOGIN')


class AdminIntegrationTest(AdminTestCase):
    """Integration tests for admin functionality"""
    
    def test_admin_index_view(self):
        """Test admin index page loads correctly"""
        url = reverse('admin:index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django administration')
    
    def test_admin_app_index_view(self):
        """Test core app admin index"""
        url = reverse('admin:app_list', kwargs={'app_label': 'core'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Core')
    
    def test_all_model_admin_views_accessible(self):
        """Test all core model admin views are accessible"""
        models = [
            'user', 'accounttype', 'bankaccount', 'transactioncategory',
            'transaction', 'beneficiary', 'card', 'auditlog'
        ]
        
        for model in models:
            url = reverse(f'admin:core_{model}_changelist')
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Failed to access {model} admin")
