from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from .models import User, BankAccount, Transaction, TransactionCategory
from .serializers import (
    UserRegistrationSerializer, UserProfileSerializer, LoginSerializer,
    BankAccountSerializer, TransactionSerializer, TransferSerializer,
    SetTransactionPINSerializer, VerifyTransactionPINSerializer
)
from .utils import verbose_logging
from .crypto_utils import CryptoUtils
from django.conf import settings
import json


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
        
        return Response({
            'message': 'User registered successfully.',
            'user': UserProfileSerializer(user).data,

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
        
        return Response({
            'user': UserProfileSerializer(user).data
        })

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    @verbose_logging
    def logout(self, request):
        """Logout endpoint is not used in this cryptographic system (no JWT)."""
        return Response({'message': 'Logout not required in this system.'}, status=status.HTTP_200_OK)

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
    permission_classes = [permissions.AllowAny]  # Crypto will handle auth
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        # User is determined by public key in the request
        return BankAccount.objects.none()  # Will be set after crypto auth

    def initial(self, request, *args, **kwargs):
        # Unified cryptographic verification and decryption
        encrypted_payload = request.data.get('payload')
        signature = request.data.get('signature')
        client_pubkey = request.data.get('client_pubkey')
        if not (encrypted_payload and signature and client_pubkey):
            return Response({'error': 'Missing cryptographic fields.'}, status=status.HTTP_400_BAD_REQUEST)
        # Verify signature
        if not CryptoUtils.verify_signature(client_pubkey, encrypted_payload.encode(), signature):
            return Response({'error': 'Invalid signature.'}, status=status.HTTP_401_UNAUTHORIZED)
        # Derive session key
        session_key = CryptoUtils.derive_session_key(
            CryptoUtils.get_server_private_key(), client_pubkey
        )
        # Decrypt payload
        try:
            decrypted = CryptoUtils.decrypt(encrypted_payload, session_key)
            request._decrypted_data = json.loads(decrypted.decode())
        except Exception as e:
            return Response({'error': f'Decryption failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        # Set user for queryset
        user = CryptoUtils.get_user_by_public_key(client_pubkey)
        if not user:
            return Response({'error': 'Unknown client public key.'}, status=status.HTTP_401_UNAUTHORIZED)
        request.user = user
        return super().initial(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        # Use decrypted data if needed
        self.queryset = BankAccount.objects.filter(user=request.user)
        response = super().list(request, *args, **kwargs)
        # Encrypt and sign response
        session_key = CryptoUtils.derive_session_key(
            CryptoUtils.get_server_private_key(), request.data.get('client_pubkey')
        )
        encrypted = CryptoUtils.encrypt(json.dumps(response.data).encode(), session_key)
        signature = CryptoUtils.sign_message(CryptoUtils.get_server_private_key(), encrypted.encode())
        return Response({'payload': encrypted, 'signature': signature, 'server_pubkey': CryptoUtils.get_server_public_key()})

    @action(detail=True, methods=['get'])
    @verbose_logging
    def transactions(self, request, pk=None):
        account = self.get_object()
        transactions = Transaction.objects.filter(account=account).order_by('-created_at')
        serializer = TransactionSerializer(transactions, many=True)
        # Encrypt and sign response
        session_key = CryptoUtils.derive_session_key(
            CryptoUtils.get_server_private_key(), request.data.get('client_pubkey')
        )
        encrypted = CryptoUtils.encrypt(json.dumps(serializer.data).encode(), session_key)
        signature = CryptoUtils.sign_message(CryptoUtils.get_server_private_key(), encrypted.encode())
        return Response({'payload': encrypted, 'signature': signature, 'server_pubkey': CryptoUtils.get_server_public_key()})


class TransactionViewSet(viewsets.GenericViewSet):
    """Handles listing transactions and making transfers."""
    permission_classes = [permissions.AllowAny]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.none()  # Will be set after crypto auth

    def initial(self, request, *args, **kwargs):
        encrypted_payload = request.data.get('payload')
        signature = request.data.get('signature')
        client_pubkey = request.data.get('client_pubkey')
        if not (encrypted_payload and signature and client_pubkey):
            return Response({'error': 'Missing cryptographic fields.'}, status=status.HTTP_400_BAD_REQUEST)
        if not CryptoUtils.verify_signature(client_pubkey, encrypted_payload.encode(), signature):
            return Response({'error': 'Invalid signature.'}, status=status.HTTP_401_UNAUTHORIZED)
        session_key = CryptoUtils.derive_session_key(
            CryptoUtils.get_server_private_key(), client_pubkey
        )
        try:
            decrypted = CryptoUtils.decrypt(encrypted_payload, session_key)
            request._decrypted_data = json.loads(decrypted.decode())
        except Exception as e:
            return Response({'error': f'Decryption failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        user = CryptoUtils.get_user_by_public_key(client_pubkey)
        if not user:
            return Response({'error': 'Unknown client public key.'}, status=status.HTTP_401_UNAUTHORIZED)
        request.user = user
        return super().initial(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='all')
    @verbose_logging
    def list_transactions(self, request):
        self.queryset = Transaction.objects.filter(account__user=request.user).order_by('-created_at')
        response = super().list(request)
        session_key = CryptoUtils.derive_session_key(
            CryptoUtils.get_server_private_key(), request.data.get('client_pubkey')
        )
        encrypted = CryptoUtils.encrypt(json.dumps(response.data).encode(), session_key)
        signature = CryptoUtils.sign_message(CryptoUtils.get_server_private_key(), encrypted.encode())
        return Response({'payload': encrypted, 'signature': signature, 'server_pubkey': CryptoUtils.get_server_public_key()})

    @action(detail=False, methods=['post'], serializer_class=TransferSerializer)
    @verbose_logging
    def transfer(self, request):
        # Use decrypted data for transfer
        serializer = self.get_serializer(data=request._decrypted_data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        source_account = serializer.validated_data['source_account']
        destination_account = serializer.validated_data['destination_account']
        amount = serializer.validated_data['amount']
        description = serializer.validated_data.get('description', 'Fund Transfer')
        try:
            with transaction.atomic():
                source_account.balance -= amount
                source_account.save()
                destination_account.balance += amount
                destination_account.save()
                transfer_category, _ = TransactionCategory.objects.get_or_create(name='Transfer')
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
            session_key = CryptoUtils.derive_session_key(
                CryptoUtils.get_server_private_key(), request.data.get('client_pubkey')
            )
            resp = {'message': 'Transfer successful.', 'source_account_balance': source_account.balance}
            encrypted = CryptoUtils.encrypt(json.dumps(resp).encode(), session_key)
            signature = CryptoUtils.sign_message(CryptoUtils.get_server_private_key(), encrypted.encode())
            return Response({'payload': encrypted, 'signature': signature, 'server_pubkey': CryptoUtils.get_server_public_key()}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred during the transfer: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
