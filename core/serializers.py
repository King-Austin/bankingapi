from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction as db_transaction
from decimal import Decimal
from .models import (
    User, BankAccount, Transaction, Beneficiary, 
    Card, AccountType, TransactionCategory
)


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 
                 'last_name', 'phone_number', 'date_of_birth', 'address')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        
        with db_transaction.atomic():
            # Create user
            user = User.objects.create_user(**validated_data)
            
            # Get or create default account type (Savings)
            account_type, created = AccountType.objects.get_or_create(
                name='Savings',
                defaults={
                    'description': 'Standard savings account',
                    'minimum_balance': Decimal('0.00'),
                    'interest_rate': Decimal('2.50'),
                    'monthly_fee': Decimal('0.00'),
                    'transaction_limit_daily': Decimal('500000.00'),
                    'is_active': True
                }
            )
            
            # Create primary bank account with demo funds
            demo_amount = Decimal('50000.00')  # ₦50,000 demo amount
            bank_account = BankAccount.objects.create(
                user=user,
                account_type=account_type,
                balance=demo_amount,
                available_balance=demo_amount,
                is_primary=True,
                status='ACTIVE'
            )
            
            # Create welcome transaction record
            try:
                # Get or create bonus category
                bonus_category, _ = TransactionCategory.objects.get_or_create(
                    name='Bonus',
                    defaults={'description': 'Welcome bonus and promotions'}
                )
                
                Transaction.objects.create(
                    account=bank_account,
                    transaction_type='CREDIT',
                    amount=demo_amount,
                    balance_before=Decimal('0.00'),  # Account started with 0
                    balance_after=demo_amount,       # After credit, balance is demo_amount
                    description='Welcome bonus - Demo funds',
                    reference_number=f'DEMO{bank_account.account_number}',
                    status='COMPLETED',
                    category=bonus_category
                )
            except Exception as e:
                # Log the error but don't fail registration
                print(f"Failed to create welcome transaction: {e}")
                # The account is still created with the balance
            
            return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                 'phone_number', 'date_of_birth', 'address', 'is_verified', 
                 'two_factor_enabled', 'date_joined')
        read_only_fields = ('id', 'username', 'is_verified', 'date_joined')


class AccountTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountType
        fields = '__all__'


class BankAccountSerializer(serializers.ModelSerializer):
    account_type_name = serializers.CharField(source='account_type.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = BankAccount
        fields = ('id', 'account_number', 'account_type', 'account_type_name', 
                 'balance', 'available_balance', 'status', 'is_primary', 
                 'user_name', 'created_at', 'updated_at')
        read_only_fields = ('id', 'account_number', 'balance', 'available_balance', 
                           'created_at', 'updated_at')


class TransactionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionCategory
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = ('id', 'account_number', 'transaction_type', 'category', 'category_name',
                 'amount', 'balance_before', 'balance_after', 'description', 
                 'reference_number', 'status', 'recipient_account_number', 
                 'recipient_name', 'sender_account_number', 'sender_name', 
                 'created_at', 'updated_at')
        read_only_fields = ('id', 'reference_number', 'balance_before', 
                           'balance_after', 'created_at', 'updated_at')


class TransferSerializer(serializers.Serializer):
    recipient_account_number = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    description = serializers.CharField(max_length=255)
    pin = serializers.CharField(max_length=6, write_only=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class BeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Beneficiary
        fields = ('id', 'name', 'account_number', 'bank_name', 'nickname', 
                 'is_favorite', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class CardSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    
    class Meta:
        model = Card
        fields = ('id', 'account_number', 'masked_card_number', 'card_type', 
                 'cardholder_name', 'expiry_date', 'status', 'daily_limit', 
                 'is_contactless_enabled', 'is_online_enabled', 'created_at')
        read_only_fields = ('id', 'masked_card_number', 'created_at')


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value
