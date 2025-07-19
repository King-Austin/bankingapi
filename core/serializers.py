from rest_framework import serializers
from django.contrib.auth import authenticate
from django.db import transaction as db_transaction
from decimal import Decimal
import hashlib
from .models import (
    User, BankAccount, Transaction, AccountType, TransactionCategory
)


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Handles the registration of a new user, including creating their
    default bank account. This serializer is designed to match the
    consolidated User model and the frontend registration form.
    """
    # The `public_key` is submitted by the client but not part of the User model's own fields.
    # It's handled in the view or a higher-level serializer that composes this one.
    # For direct use, we expect it to be in the validated_data.
    
    class Meta:
        model = User
        # These fields are expected from the client, matching the consolidated User model
        fields = (
            'email', 'first_name', 'last_name', 'phone_number', 
            'date_of_birth', 'address', 'occupation', 'public_key', 'nin'
        )
        extra_kwargs = {
            'public_key': {'write_only': True}
        }

    def create(self, validated_data):
        """
        Creates the User, a default BankAccount, and a welcome bonus transaction.
        Sets the user password as the SHA-256 hash of the public key for consistency with Django's user model.
        """
        public_key = validated_data.get('public_key')
        if not public_key:
            raise serializers.ValidationError({'public_key': 'Public key is required.'})
        # Hash the public key (SHA-256)
        pubkey_hash = hashlib.sha256(public_key.encode('utf-8')).hexdigest()
        # Set the password to the hash of the public key
        validated_data['password'] = pubkey_hash
        with db_transaction.atomic():
            user = User.objects.create(**validated_data)
            user.set_password(pubkey_hash)
            user.save()
            # Get or create a default 'Savings' account type
            account_type, _ = AccountType.objects.get_or_create(
                name='Savings',
                defaults={
                    'description': 'Standard savings account',
                    'minimum_balance': Decimal('0.00'),
                    'interest_rate': Decimal('1.50'),
                    'is_active': True
                }
            )
            
            # Create a primary bank account for the new user with a welcome bonus
            welcome_bonus = Decimal('25000.00')  # e.g., ₦25,000
            bank_account = BankAccount.objects.create(
                user=user,
                account_type=account_type,
                balance=welcome_bonus,
                available_balance=welcome_bonus,
                is_primary=True,
                status='ACTIVE'
            )
            
            # Create a transaction record for the welcome bonus
            try:
                bonus_category, _ = TransactionCategory.objects.get_or_create(name='Bonus')
                Transaction.objects.create(
                    account=bank_account,
                    transaction_type='CREDIT',
                    amount=welcome_bonus,
                    balance_before=Decimal('0.00'),
                    balance_after=welcome_bonus,
                    description='Welcome Bonus',
                    status='COMPLETED',
                    category=bonus_category
                )
            except Exception as e:
                # Log if the bonus transaction fails, but don't fail the registration
                print(f"Warning: Could not create welcome bonus transaction for {user.email}. Error: {e}")
            
            return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying the user's profile information.
    """
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'phone_number', 
            'date_of_birth', 'address', 'occupation', 'is_verified', 'date_joined'
        )
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    """
    Handles login for the passwordless system.
    It expects a `public_key` to identify the user.
    """
    public_key = serializers.CharField(required=True)

    def validate(self, attrs):
        public_key = attrs.get('public_key')
        try:
            user = User.objects.get(public_key=public_key, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError('No active user found with the provided public key.')
        
        attrs['user'] = user
        return attrs


class SetTransactionPINSerializer(serializers.Serializer):
    """
    Serializer for setting or changing the transaction PIN.
    """
    pin = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'},
        min_length=4, max_length=4
    )
    pin_confirm = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['pin'] != attrs['pin_confirm']:
            raise serializers.ValidationError({"pin_confirm": "PINs do not match."})
        if not attrs['pin'].isdigit():
            raise serializers.ValidationError({"pin": "PIN must be numeric and 4 digits long."})
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_pin(self.validated_data['pin'])


class VerifyTransactionPINSerializer(serializers.Serializer):
    """
    Serializer for verifying the transaction PIN for an action.
    """
    pin = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'},
        min_length=4, max_length=4
    )

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must be numeric.")
        
        user = self.context['request'].user
        if not user.verify_pin(value):
            raise serializers.ValidationError("Invalid transaction PIN.")
        return value


class BankAccountSerializer(serializers.ModelSerializer):
    """
    Serializer for bank account details.
    """
    account_type = serializers.StringRelatedField()

    class Meta:
        model = BankAccount
        fields = ('id', 'account_number', 'account_type', 'balance', 
                  'available_balance', 'status', 'is_primary', 'created_at')


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for transaction details.
    """
    category = serializers.StringRelatedField()
    transaction_type = serializers.CharField(source='get_transaction_type_display')

    class Meta:
        model = Transaction
        fields = ('id', 'transaction_type', 'amount', 'description', 'status', 
                  'reference_number', 'created_at', 'balance_after', 'category')


class TransferSerializer(serializers.Serializer):
    """
    Serializer for handling fund transfers. Requires PIN verification.
    """
    source_account_id = serializers.UUIDField()
    destination_account_number = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(required=False, allow_blank=True, max_length=100)
    pin = serializers.CharField(write_only=True, required=True, min_length=4, max_length=4)

    def validate_pin(self, value):
        """
        Validates the transaction PIN against the user's stored PIN.
        """
        if not value.isdigit():
            raise serializers.ValidationError("PIN must be numeric.")
        
        user = self.context['request'].user
        if not user.verify_pin(value):
            raise serializers.ValidationError("Invalid transaction PIN.")
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        source_account_id = attrs.get('source_account_id')
        destination_account_number = attrs.get('destination_account_number')
        amount = attrs.get('amount')

        try:
            source_account = BankAccount.objects.get(id=source_account_id, user=user, status='ACTIVE')
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError("Source account not found, is not yours, or is not active.")

        if source_account.available_balance < amount:
            raise serializers.ValidationError("Insufficient funds.")

        try:
            destination_account = BankAccount.objects.get(account_number=destination_account_number, status='ACTIVE')
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError("Destination account not found or is not active.")
            
        if source_account.account_number == destination_account.account_number:
            raise serializers.ValidationError("Cannot transfer to the same account.")

        # Attach the model instances to validated_data for use in the view
        attrs['source_account'] = source_account
        attrs['destination_account'] = destination_account
        
        return attrs
