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


class PINVerificationMixin(serializers.Serializer):
    """
    A mixin for serializers that require transaction PIN verification.
    """
    pin = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Enter your 4-digit transaction PIN to authorize this action.",
        min_length=4,
        max_length=4
    )

    def validate_pin(self, value):
        """
        Check if the provided PIN is correct for the user.
        """
        if not value.isdigit():
            raise serializers.ValidationError("PIN must be numeric.")
        
        user = self.context['request'].user
        if not user.check_transaction_pin(value):
            raise serializers.ValidationError("Invalid transaction PIN.")
        return value


class SetTransactionPINSerializer(serializers.Serializer):
    """
    Serializer for setting or changing the transaction PIN.
    """
    pin = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="4-digit transaction PIN.",
        min_length=4,
        max_length=4
    )
    pin_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['pin'] != attrs['pin_confirm']:
            raise serializers.ValidationError({"pin_confirm": "PINs do not match."})
        if not attrs['pin'].isdigit():
            raise serializers.ValidationError({"pin": "PIN must be numeric."})
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_transaction_pin(self.validated_data['pin'])
        user.save()


class VerifyTransactionPINSerializer(serializers.Serializer):
    """
    Serializer for verifying the transaction PIN.
    """
    pin = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="4-digit transaction PIN.",
        min_length=4,
        max_length=4
    )

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must be numeric.")
        return value

    def verify(self):
        user = self.context['request'].user
        return user.check_transaction_pin(self.validated_data['pin'])


class BeneficiarySerializer(serializers.ModelSerializer):
    """
    Serializer for beneficiary details.
    """
    class Meta:
        model = Beneficiary
        fields = ('id', 'user', 'name', 'account_number', 'bank_name', 'is_active')
        read_only_fields = ('id', 'user')


class BankAccountSerializer(serializers.ModelSerializer):
    """
    Serializer for bank account details.
    """
    account_type = serializers.StringRelatedField()

    class Meta:
        model = BankAccount
        fields = ('id', 'account_number', 'account_type', 'balance', 
                  'available_balance', 'status', 'is_primary', 'created_at')


class AccountTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountType
        fields = '__all__'


class TransactionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionCategory
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    transaction_type = serializers.CharField(source='get_transaction_type_display')

    class Meta:
        model = Transaction
        fields = ('id', 'transaction_type', 'amount', 'description', 'status', 
                  'reference_number', 'created_at', 'balance_after', 'category')


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = ('id', 'user', 'card_number', 'card_type', 'expiry_date', 
                  'cvv', 'is_active', 'created_at')
        read_only_fields = ('id', 'card_number', 'created_at')


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])

        if not user:
            raise serializers.ValidationError('Invalid credentials')
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled')
        
        attrs['user'] = user
        return attrs


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


class TransferSerializer(PINVerificationMixin, serializers.Serializer):
    """
    Serializer for handling fund transfers between accounts.
    Requires PIN for authorization.
    """
    from_account = serializers.CharField()
    to_account = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_amount(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("Transfer amount must be positive.")
        return value

    def validate(self, attrs):
        # The PIN is validated by the PINVerificationMixin's `validate_pin` method
        # which is automatically called by DRF. We just need to pop it here.
        attrs.pop('pin', None)
        
        from_account_num = attrs['from_account']
        to_account_num = attrs['to_account']
        amount = attrs['amount']
        user = self.context['request'].user

        if from_account_num == to_account_num:
            raise serializers.ValidationError("Cannot transfer to the same account.")

        try:
            from_account = BankAccount.objects.get(account_number=from_account_num, user=user)
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError("Source account not found or does not belong to you.")

        try:
            to_account = BankAccount.objects.get(account_number=to_account_num)
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError("Destination account not found.")

        if from_account.status != 'ACTIVE':
            raise serializers.ValidationError("Source account is not active.")
            
        if to_account.status != 'ACTIVE':
            raise serializers.ValidationError("Destination account is not active.")

        if from_account.available_balance < amount:
            raise serializers.ValidationError("Insufficient funds.")

        attrs['from_account_obj'] = from_account
        attrs['to_account_obj'] = to_account
        return attrs

    def save(self):
        from_account = self.validated_data['from_account_obj']
        to_account = self.validated_data['to_account_obj']
        amount = self.validated_data['amount']
        description = self.validated_data.get('description', 'Fund Transfer')

        try:
            with db_transaction.atomic():
                # Debit from sender
                from_account.balance -= amount
                from_account.available_balance -= amount
                from_account.save()

                # Credit to receiver
                to_account.balance += amount
                to_account.available_balance += amount
                to_account.save()

                # Get or create transfer category
                transfer_category, _ = TransactionCategory.objects.get_or_create(
                    name='Transfer',
                    defaults={'description': 'Peer-to-peer or internal transfers'}
                )

                # Create transaction records
                debit_transaction = Transaction.objects.create(
                    account=from_account,
                    transaction_type='DEBIT',
                    amount=amount,
                    description=f"Transfer to {to_account.user.get_full_name()} ({to_account.account_number})",
                    status='COMPLETED',
                    category=transfer_category,
                    balance_before=from_account.balance + amount,
                    balance_after=from_account.balance
                )
                
                credit_transaction = Transaction.objects.create(
                    account=to_account,
                    transaction_type='CREDIT',
                    amount=amount,
                    description=f"Transfer from {from_account.user.get_full_name()} ({from_account.account_number})",
                    status='COMPLETED',
                    category=transfer_category,
                    balance_before=to_account.balance - amount,
                    balance_after=to_account.balance
                )
                
                return {
                    'success': True,
                    'message': 'Transfer successful.',
                    'debit_transaction_id': debit_transaction.id,
                    'credit_transaction_id': credit_transaction.id
                }
        except Exception as e:
            # In a real application, you would log this error thoroughly.
            # For now, we raise a validation error to inform the user.
            raise serializers.ValidationError(f"Transfer failed due to a server error: {str(e)}")
