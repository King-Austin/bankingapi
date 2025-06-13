from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import (
    User, BankAccount, Transaction, Beneficiary, Card, 
    AccountType, TransactionCategory, AuditLog
)
from .serializers import (
    UserRegistrationSerializer, UserProfileSerializer, LoginSerializer,
    BankAccountSerializer, TransactionSerializer, TransferSerializer,
    BeneficiarySerializer, CardSerializer, ChangePasswordSerializer,
    AccountTypeSerializer, TransactionCategorySerializer
)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """
    Simple health check endpoint to verify backend is running
    """
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'message': 'Banking API is running'
    }, status=status.HTTP_200_OK)


class AuthViewSet(viewsets.GenericViewSet):
    """
    Authentication related endpoints
    """
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action_type='LOGIN',
                description='User registered and logged in',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return Response({
                'user': UserProfileSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action_type='LOGIN',
                description='User logged in',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return Response({
                'user': UserProfileSerializer(user).data,
                'token': token.key
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        if request.user.is_authenticated:
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='LOGOUT',
                description='User logged out',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            # Delete token
            try:
                request.user.auth_token.delete()
            except:
                pass
            
            logout(request)
        return Response({'message': 'Successfully logged out'})


class UserViewSet(viewsets.GenericViewSet):
    """
    User profile management
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def profile(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        serializer = UserProfileSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='ACCOUNT_UPDATE',
                description='Profile updated',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='PASSWORD_CHANGE',
                description='Password changed',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BankAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Bank account management
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        account = self.get_object()
        transactions = Transaction.objects.filter(account=account)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        account = self.get_object()
        return Response({
            'account_number': account.account_number,
            'balance': account.balance,
            'available_balance': account.available_balance
        })


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Transaction history and management
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        user_accounts = BankAccount.objects.filter(user=self.request.user)
        return Transaction.objects.filter(account__in=user_accounts)

    @action(detail=False, methods=['post'])
    def transfer(self, request):
        serializer = TransferSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get sender's primary account
        try:
            sender_account = BankAccount.objects.get(
                user=request.user, is_primary=True, status='ACTIVE'
            )
        except BankAccount.DoesNotExist:
            return Response(
                {'error': 'No active primary account found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate PIN
        if sender_account.pin != serializer.validated_data['pin']:
            return Response(
                {'error': 'Invalid PIN'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if recipient account exists
        recipient_account_number = serializer.validated_data['recipient_account_number']
        try:
            recipient_account = BankAccount.objects.get(
                account_number=recipient_account_number, status='ACTIVE'
            )
        except BankAccount.DoesNotExist:
            return Response(
                {'error': 'Recipient account not found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        amount = serializer.validated_data['amount']
        description = serializer.validated_data['description']

        # Check balance
        if sender_account.balance < amount:
            return Response(
                {'error': 'Insufficient balance'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Perform transfer with database transaction
        try:
            with transaction.atomic():
                # Get transfer category
                transfer_category, _ = TransactionCategory.objects.get_or_create(
                    name='Transfer',
                    defaults={'description': 'Money Transfer'}
                )

                # Debit sender
                sender_balance_before = sender_account.balance
                sender_account.balance -= amount
                sender_account.available_balance -= amount
                sender_account.save()

                # Credit recipient
                recipient_balance_before = recipient_account.balance
                recipient_account.balance += amount
                recipient_account.available_balance += amount
                recipient_account.save()

                # Create debit transaction
                debit_transaction = Transaction.objects.create(
                    account=sender_account,
                    transaction_type='DEBIT',
                    category=transfer_category,
                    amount=amount,
                    balance_before=sender_balance_before,
                    balance_after=sender_account.balance,
                    description=f"Transfer to {recipient_account.user.get_full_name()}",
                    recipient_account_number=recipient_account_number,
                    recipient_name=recipient_account.user.get_full_name(),
                    status='COMPLETED',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )

                # Create credit transaction
                credit_transaction = Transaction.objects.create(
                    account=recipient_account,
                    transaction_type='CREDIT',
                    category=transfer_category,
                    amount=amount,
                    balance_before=recipient_balance_before,
                    balance_after=recipient_account.balance,
                    description=f"Transfer from {sender_account.user.get_full_name()}",
                    sender_account_number=sender_account.account_number,
                    sender_name=sender_account.user.get_full_name(),
                    status='COMPLETED',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )

                # Create audit log
                AuditLog.objects.create(
                    user=request.user,
                    action_type='TRANSACTION',
                    description=f'Transfer of {amount} to {recipient_account_number}',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT'),
                    additional_data={
                        'amount': str(amount),
                        'recipient_account': recipient_account_number,
                        'reference_number': debit_transaction.reference_number
                    }
                )

                return Response({
                    'message': 'Transfer successful',
                    'reference_number': debit_transaction.reference_number,
                    'amount': amount,
                    'recipient_account': recipient_account_number,
                    'new_balance': sender_account.balance
                })

        except Exception as e:
            return Response(
                {'error': 'Transfer failed. Please try again.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BeneficiaryViewSet(viewsets.ModelViewSet):
    """
    Beneficiary management
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BeneficiarySerializer

    def get_queryset(self):
        return Beneficiary.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        beneficiary = serializer.save(user=self.request.user)
        
        # Create audit log
        AuditLog.objects.create(
            user=self.request.user,
            action_type='BENEFICIARY_OP',
            description=f'Added beneficiary: {beneficiary.name}',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT')
        )


class CardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Card management
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CardSerializer

    def get_queryset(self):
        user_accounts = BankAccount.objects.filter(user=self.request.user)
        return Card.objects.filter(account__in=user_accounts)

    @action(detail=True, methods=['post'])
    def block_card(self, request, pk=None):
        card = self.get_object()
        card.status = 'BLOCKED'
        card.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action_type='CARD_OPERATION',
            description=f'Blocked card: {card.masked_card_number}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response({'message': 'Card blocked successfully'})

    @action(detail=True, methods=['post'])
    def unblock_card(self, request, pk=None):
        card = self.get_object()
        card.status = 'ACTIVE'
        card.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action_type='CARD_OPERATION',
            description=f'Unblocked card: {card.masked_card_number}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response({'message': 'Card unblocked successfully'})


class AccountTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Account types available
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = AccountTypeSerializer
    queryset = AccountType.objects.filter(is_active=True)


class TransactionCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Transaction categories
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransactionCategorySerializer
    queryset = TransactionCategory.objects.filter(is_active=True)
