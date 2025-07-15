from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.utils import timezone
from .models import User, BankAccount, Transaction, TransactionCategory
from .serializers import (
    UserRegistrationSerializer, UserProfileSerializer, LoginSerializer,
    BankAccountSerializer, TransactionSerializer, TransferSerializer,
    SetTransactionPINSerializer, VerifyTransactionPINSerializer
)
from .utils import verbose_logging


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@verbose_logging
def health_check(request):
    """A simple health check endpoint to confirm the API is running."""
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'message': 'Banking API is operational.'
    }, status=status.HTTP_200_OK)


class AuthViewSet(viewsets.GenericViewSet):
    """Handles user registration, login, logout, and PIN management."""
    permission_classes = [permissions.AllowAny]

    @action(
            detail=False,
             methods=['post'], 
             serializer_class=UserRegistrationSerializer,
               permission_classes=[permissions.AllowAny])
    @verbose_logging
    def register(self, request):
        """
        Registers a new user. The middleware provides the decrypted payload.
        """
        # Directly use flat payload from the client
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'User registered successfully.',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], serializer_class=LoginSerializer)
    @verbose_logging
    def login(self, request):
        """
        Logs a user in using their public key and returns JWTs.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserProfileSerializer(user).data
        })

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    @verbose_logging
    def logout(self, request):
        """Blacklists the user's refresh token."""
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            return Response({'error': 'Invalid or missing refresh token.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated], serializer_class=SetTransactionPINSerializer)
    @verbose_logging
    def set_pin(self, request):
        """Sets or updates the user's transaction PIN."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'PIN set successfully.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated], serializer_class=VerifyTransactionPINSerializer)
    @verbose_logging
    def verify_pin(self, request):
        """Verifies the user's transaction PIN."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response({'verified': True}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """Provides read-only access to the user's profile."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        return User.objects.filter(pk=self.request.user.pk)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """A convenience endpoint to get the current user's profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class BankAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """Provides read-only access to a user's bank accounts."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    @verbose_logging
    def transactions(self, request, pk=None):
        """Gets all transactions for a specific account."""
        account = self.get_object()
        transactions = Transaction.objects.filter(account=account).order_by('-created_at')
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class TransactionViewSet(viewsets.GenericViewSet):
    """Handles listing transactions and making transfers."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(account__user=self.request.user)

    @action(detail=False, methods=['get'], url_path='all')
    @verbose_logging
    def list_transactions(self, request):
        """Lists all transactions for the authenticated user."""
        queryset = self.get_queryset().order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], serializer_class=TransferSerializer)
    @verbose_logging
    def transfer(self, request):
        """
        Handles a secure, atomic fund transfer between accounts.
        PIN verification is handled within the serializer.
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        source_account = serializer.validated_data['source_account']
        destination_account = serializer.validated_data['destination_account']
        amount = serializer.validated_data['amount']
        description = serializer.validated_data.get('description', 'Fund Transfer')

        try:
            with transaction.atomic():
                # Perform the debit and credit
                source_account.balance -= amount
                source_account.save()

                destination_account.balance += amount
                destination_account.save()

                # Get or create the 'Transfer' category
                transfer_category, _ = TransactionCategory.objects.get_or_create(name='Transfer')

                # Create transaction records for both parties
                Transaction.objects.create(
                    account=source_account,
                    transaction_type='DEBIT',
                    amount=amount,
                    description=f"Transfer to {destination_account.user.get_full_name()}",
                    category=transfer_category,
                    status='COMPLETED',
                    balance_before=source_account.balance + amount,
                    balance_after=source_account.balance
                )
                Transaction.objects.create(
                    account=destination_account,
                    transaction_type='CREDIT',
                    amount=amount,
                    description=f"Transfer from {source_account.user.get_full_name()}",
                    category=transfer_category,
                    status='COMPLETED',
                    balance_before=destination_account.balance - amount,
                    balance_after=destination_account.balance
                )

            return Response({
                'message': 'Transfer successful.',
                'source_account_balance': source_account.balance
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'An unexpected error occurred during the transfer: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
