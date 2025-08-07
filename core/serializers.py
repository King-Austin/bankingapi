from ipaddress import ip_address
from rest_framework import serializers
from django.db import transaction, IntegrityError
from .models import User, Transaction
from decimal import Decimal
import hashlib

class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for Transaction model.
    Provides human-readable representations for category and transaction type.
    """
    category = serializers.StringRelatedField()
    transaction_type = serializers.CharField(source='get_transaction_type_display')

    class Meta:
        model = Transaction
        fields = (
            'id', 'transaction_type', 'amount', 'description', 'status',
            'reference_number', 'created_at', 'balance_after', 'category'
        )


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Handles user registration, including validation of unique fields,
    account number generation, and initial welcome bonus transaction.
    """

    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'public_key', 'phone_number', 'date_of_birth', 'address',
            'occupation', 'nin', 'bvn', 'is_verified',
        )

    def validate(self, attrs):
        print("\n[UserRegistrationSerializer] Starting validation of user registration data.")
        unique_fields = ['username', 'email', 'phone_number', 'nin', 'bvn']
        for field in unique_fields:
            value = attrs.get(field)

            print(f"[UserRegistrationSerializer] Checking uniqueness for {field}: {value}")
            if value and User.objects.filter(**{field: value}).exists():
                print(f"[UserRegistrationSerializer] Duplicate found for {field}: {value}")
                raise serializers.ValidationError({field: f"This {field.replace('_', ' ')} is already registered."})
        print("[UserRegistrationSerializer] Validation passed for all unique fields.")
        return attrs

    def generate_account_number(self, transaction_data):
        print("\n[UserRegistrationSerializer] Generating account number from phone number.")
        phone_number = transaction_data.get('phone_number', None)
        print(f"[UserRegistrationSerializer] Raw phone number: {phone_number}")
        phone_digits = phone_number.lstrip('0').replace('+234', '').replace(' ', '').replace('-', '') if phone_number else ''
        print(f"[UserRegistrationSerializer] Processed phone digits: {phone_digits}")
        if len(phone_digits) >= 10:
            account_number = phone_digits[:10]
            print(f"[UserRegistrationSerializer] Generated account number: {account_number}")
            return account_number
        print("[UserRegistrationSerializer] Phone number does not have enough digits after formatting.")
        raise serializers.ValidationError("Phone number must contain at least 10 digits after formatting.")
    
    def create(self, validated_data):
        print("\n[UserRegistrationSerializer] Creating user with validated data:", validated_data)
        public_key = validated_data.pop('public_key')
        print("[UserRegistrationSerializer] Public key received:", public_key)
        pubkey_hash = hashlib.sha256(public_key.encode('utf-8')).hexdigest()
        print("[UserRegistrationSerializer] Public key hash generated:", pubkey_hash)
        validated_data['password'] = pubkey_hash

        print("[UserRegistrationSerializer] Generating account number...")
        validated_data['account_number'] = self.generate_account_number(validated_data)
        print("[UserRegistrationSerializer] Account number set:", validated_data['account_number'])

        try:
            print("[UserRegistrationSerializer] Entering atomic transaction block for user creation.")
            with transaction.atomic():
                
                print("[UserRegistrationSerializer] Creating User object in database...")
                user = User.objects.create(**validated_data, public_key=public_key)
                print("[UserRegistrationSerializer] User object created:", user)
                user.set_password(pubkey_hash)
                user.save()
                print("[UserRegistrationSerializer] User password set and user saved.")

                # Add welcome bonus transaction
                print("[UserRegistrationSerializer] Creating welcome bonus transaction...")
                welcome_bonus = Decimal('50000.00')
                Transaction.objects.create(

                    account=User.objects.get(id=user.id),
                    transaction_type='CREDIT',
                    amount=welcome_bonus,
                    balance_before=Decimal('0.00'),
                    balance_after=welcome_bonus,
                    description='Welcome Bonus',
                    status ='COMPLETED',
                    sender_name='SecureCipher Bank',
                    sender_account_number='0000000000'
                )
                print("[UserRegistrationSerializer] Welcome bonus transaction created.")
                print("[UserRegistrationSerializer] User registration complete.")
                return user
        except IntegrityError:
            print("[UserRegistrationSerializer] IntegrityError: A user with other unique field already exists.")
            raise serializers.ValidationError({'error': 'A user with other unique field already exists.'})

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'public_key', 'phone_number', 'date_of_birth', 'address',
            'occupation', 'nin', 'bvn', 'is_verified', 'account_number', 'balance', 'account_type', 'status', 'is_primary', 'created_at', 'updated_at'
        )
        read_only_fields = fields

class TransferSerializer(serializers.Serializer):
    source_account_id = serializers.UUIDField()
    destination_account_number = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    description = serializers.CharField(required=False, allow_blank=True, max_length=100)

    def validate(self, attrs):
        print("\n[TransferSerializer] Starting transfer validation.")
        print(f"[TransferSerializer] Looking up source account with public_key: {attrs.get('public_key')}")
        source_account = User.objects.get(public_key=attrs.get('public_key'))
        if not source_account:
            print("[TransferSerializer] Source account not found or not active.")
            raise serializers.ValidationError("User not found or is not active.")
        destination_account_number = attrs.get('destination_account_number')
        amount = attrs.get('amount')
        print(f"[TransferSerializer] Source account balance: {source_account.available_balance}, Transfer amount: {amount}")

        if source_account.available_balance < amount:
            print("[TransferSerializer] Insufficient funds for transfer.")
            raise serializers.ValidationError("Insufficient funds.")

        try:
            print(f"[TransferSerializer] Looking up destination account: {destination_account_number}")
            destination_account = User.objects.get(account_number=destination_account_number)
        except User.DoesNotExist:
            print("[TransferSerializer] Destination account not found.")
            raise serializers.ValidationError("Destination account not found.")

        if source_account.account_number == destination_account.account_number:
            print("[TransferSerializer] Attempted transfer to same account.")
            raise serializers.ValidationError("Cannot transfer to the same account.")

        print("[TransferSerializer] Transfer validation passed.")
        attrs['source_account'] = source_account
        attrs['destination_account'] = destination_account
        return attrs

