from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import random
import string


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)  # Make email unique
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    national_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    # This field will store the salted and hashed transaction PIN.
    transaction_pin_hash = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} - {self.get_full_name()}"

    class Meta:
        db_table = 'users'


class AccountType(models.Model):
    """
    Different types of bank accounts (Savings, Checking, Business, etc.)
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    minimum_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    monthly_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    transaction_limit_daily = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'account_types'


class BankAccount(models.Model):
    """
    Bank Account model for users
    """
    ACCOUNT_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('SUSPENDED', 'Suspended'),
        ('CLOSED', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    account_type = models.ForeignKey(AccountType, on_delete=models.PROTECT)
    account_number = models.CharField(max_length=20, unique=True, editable=False)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    available_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    status = models.CharField(max_length=10, choices=ACCOUNT_STATUS_CHOICES, default='ACTIVE')
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = self.generate_account_number()
        super().save(*args, **kwargs)

    def generate_account_number(self):
        """Generate account number based on phone number (remove leading zero)"""
        if self.user and self.user.phone_number:
            # Remove leading zero and take up to 10 digits
            phone_digits = self.user.phone_number.lstrip('0').replace('+234', '').replace(' ', '').replace('-', '')
            if len(phone_digits) >= 10:
                return phone_digits[:10]
            else:
                # If phone number is too short, pad with random digits
                remaining_digits = 10 - len(phone_digits)
                random_digits = ''.join(random.choices(string.digits, k=remaining_digits))
                return phone_digits + random_digits
        else:
            # Fallback to random 10-digit number
            return ''.join(random.choices(string.digits, k=10))

    def __str__(self):
        return f"{self.user.username} - {self.account_number}"

    class Meta:
        db_table = 'bank_accounts'
        unique_together = ['user', 'is_primary']


class TransactionCategory(models.Model):
    """
    Categories for transactions (Transfer, Payment, Deposit, etc.)
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # For UI icons
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'transaction_categories'
        verbose_name_plural = 'Transaction Categories'


class Transaction(models.Model):
    """
    Transaction model to record all financial transactions
    """
    TRANSACTION_TYPE_CHOICES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    ]

    TRANSACTION_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=6, choices=TRANSACTION_TYPE_CHOICES)
    category = models.ForeignKey(TransactionCategory, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.CharField(max_length=255)
    reference_number = models.CharField(max_length=50, unique=True, editable=False)
    status = models.CharField(max_length=10, choices=TRANSACTION_STATUS_CHOICES, default='PENDING')
    
    # For transfers and external transactions
    recipient_account_number = models.CharField(max_length=20, null=True, blank=True)
    recipient_name = models.CharField(max_length=100, null=True, blank=True)
    sender_account_number = models.CharField(max_length=20, null=True, blank=True)
    sender_name = models.CharField(max_length=100, null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        super().save(*args, **kwargs)

    def generate_reference_number(self):
        """Generate a unique reference number"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_digits = ''.join(random.choices(string.digits, k=4))
        reference = f"TXN{timestamp}{random_digits}"
        
        # Ensure uniqueness
        while Transaction.objects.filter(reference_number=reference).exists():
            random_digits = ''.join(random.choices(string.digits, k=4))
            reference = f"TXN{timestamp}{random_digits}"
        
        return reference

    def __str__(self):
        return f"{self.reference_number} - {self.amount}"

    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']


class Beneficiary(models.Model):
    """
    Saved beneficiaries for easy transfers
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='beneficiaries')
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100, default='SecureCipher Bank')
    nickname = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.account_name} - {self.account_number}"

    class Meta:
        db_table = 'beneficiaries'
        unique_together = ['user', 'account_number']


class Card(models.Model):
    """
    Bank cards (Debit/Credit cards)
    """
    CARD_TYPE_CHOICES = [
        ('DEBIT', 'Debit Card'),
        ('CREDIT', 'Credit Card'),
    ]

    CARD_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('BLOCKED', 'Blocked'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='cards')
    card_number = models.CharField(max_length=16, unique=True, editable=False)
    card_type = models.CharField(max_length=6, choices=CARD_TYPE_CHOICES)
    cardholder_name = models.CharField(max_length=100)
    expiry_date = models.DateField()
    cvv = models.CharField(max_length=3, editable=False)
    pin = models.CharField(max_length=4, editable=False)
    status = models.CharField(max_length=10, choices=CARD_STATUS_CHOICES, default='ACTIVE')
    daily_limit = models.DecimalField(max_digits=10, decimal_places=2, default=100000.00)
    is_international = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.card_number:
            self.card_number = self.generate_card_number()
        if not self.cvv:
            self.cvv = self.generate_cvv()
        if not self.pin:
            self.pin = self.generate_pin()
        super().save(*args, **kwargs)

    def generate_card_number(self):
        """Generate a unique 16-digit card number"""
        while True:
            card_number = '4' + ''.join(random.choices(string.digits, k=15))  # Starts with 4 (Visa)
            if not Card.objects.filter(card_number=card_number).exists():
                return card_number

    def generate_cvv(self):
        """Generate a 3-digit CVV"""
        return ''.join(random.choices(string.digits, k=3))

    def generate_pin(self):
        """Generate a 4-digit PIN"""
        return ''.join(random.choices(string.digits, k=4))

    def __str__(self):
        return f"{self.cardholder_name} - ****{self.card_number[-4:]}"

    class Meta:
        db_table = 'cards'


class AuditLog(models.Model):
    """
    Audit log for tracking user actions
    """
    ACTION_TYPE_CHOICES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('TRANSACTION', 'Transaction'),
        ('ACCOUNT_UPDATE', 'Account Update'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('CARD_OPERATION', 'Card Operation'),
        ('BENEFICIARY_OP', 'Beneficiary Operation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=25, choices=ACTION_TYPE_CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    additional_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action_type} - {self.created_at}"

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
