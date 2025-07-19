from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import random
import string
from django.contrib.auth.hashers import make_password, check_password


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model for the passwordless system.
    - Email is the unique identifier.
    - `public_key` stores the user's cryptographic key for authentication.
    - `transaction_pin_hash` stores the hash for transaction authorization.
    """
    # Remove username and use email as the primary identifier
    username = None
    email = models.EmailField(unique=True)

    # Personal and contact information
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    phone_number = models.CharField(max_length=15, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    nin = models.CharField(
        max_length=11,
        unique=True,
        help_text="Nigerian National Identification Number",
        null=True,
        blank=True
    )

    # Security fields
    public_key = models.TextField(unique=True, blank=True, null=True)
    is_verified = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number']  # removed 'nin' temporarily to avoid migration issues

    objects = UserManager()

    def __str__(self):
        return self.email

    def set_pin(self, raw_pin):
        """Hashes and sets the transaction PIN."""
        self.transaction_pin_hash = make_password(raw_pin)
        self.save()

    def verify_pin(self, raw_pin):
        """Verifies a raw PIN against the stored hash."""
        return check_password(raw_pin, self.transaction_pin_hash)

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
        return f"{self.user.email} - {self.account_number}"

    class Meta:
        db_table = 'bank_accounts'
        unique_together = ('user', 'is_primary')


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
