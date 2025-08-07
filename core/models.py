from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import random
import string
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Includes extra fields for phone, NIN, BVN, and now account details.
    """
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
    bvn = models.CharField(
        max_length=11,
        unique=True,
        help_text="Bank Verification Number",
        null=True,
        blank=True
    )
    public_key = models.TextField(unique=True, blank=True, null=True)

    # Account fields (merged from BankAccount)
    ACCOUNT_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('SUSPENDED', 'Suspended'),
        ('CLOSED', 'Closed'),
    ]
    account_number = models.CharField(max_length=20, unique=True, editable=False)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    account_type = models.CharField(max_length=50, default='Savings')
    status = models.CharField(max_length=10, choices=ACCOUNT_STATUS_CHOICES, default='ACTIVE')
    is_primary = models.BooleanField(default=True)

    # Other meta data
    is_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)



    def __str__(self):
        return self.username

    class Meta:
        db_table = 'user'


# class TransactionCategory(models.Model):
#     name = models.CharField(max_length=50, unique=True)
#     description = models.TextField(blank=True)
#     icon = models.CharField(max_length=50, blank=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name

#     class Meta:
#         db_table = 'transaction_categories'
#         verbose_name_plural = 'Transaction Categories'


class Transaction(models.Model):
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
    account = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions',
        db_column='account_id'
    )
    transaction_type = models.CharField(max_length=6, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.CharField(max_length=255)
    reference_number = models.CharField(max_length=50, unique=True, editable=False)
    status = models.CharField(max_length=10, choices=TRANSACTION_STATUS_CHOICES, default='PENDING')
    recipient_account_number = models.CharField(max_length=20, null=True, blank=True)
    recipient_name = models.CharField(max_length=100, null=True, blank=True)
    sender_account_number = models.CharField(max_length=20, null=True, blank=True)
    sender_name = models.CharField(max_length=100, null=True, blank=True)
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
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_digits = ''.join(random.choices(string.digits, k=4))
        reference = f"TXN{timestamp}{random_digits}"
        while Transaction.objects.filter(reference_number=reference).exists():
            random_digits = ''.join(random.choices(string.digits, k=4))
            reference = f"TXN{timestamp}{random_digits}"
        return reference

    def __str__(self):
        return f"{self.reference_number} - {self.amount}"

    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']


class ApiKeyPair(models.Model):
    label = models.CharField(max_length=50, unique=True)
    public_key = models.TextField()
    private_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_key_pairs'

    def __str__(self):
        return f"{self.label} KeyPair"
