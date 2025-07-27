from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction
from .models import User, UserProfile, BankAccount, Transaction
from .serializers import (
    UserRegistrationSerializer, UserProfileSerializer, LoginSerializer,
    BankAccountSerializer, TransactionSerializer, TransferSerializer
)
from .crypto_utils import CryptoUtils
import json

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("RegisterView: Received data:", request.data)
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        print("RegisterView: Created user:", user.username)
        accounts = BankAccount.objects.filter(user=user)
        transactions = Transaction.objects.filter(account__user=user).order_by('-created_at')
        return Response({
            'user': UserProfileSerializer(user.profile).data,
            'accounts': BankAccountSerializer(accounts, many=True).data,
            'transactions': TransactionSerializer(transactions, many=True).data
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("LoginView: Received data:", request.data)
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        print("LoginView: Authenticated user:", user.username)
        accounts = BankAccount.objects.filter(user=user)
        transactions = Transaction.objects.filter(account__user=user).order_by('-created_at')
        return Response({
            'user': UserProfileSerializer(user.profile).data,
            'accounts': BankAccountSerializer(accounts, many=True).data,
            'transactions': TransactionSerializer(transactions, many=True).data
        })

class ValidateAccountView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("ValidateAccountView: Received data:", request.data)
        payload = request.data.get('payload')
        signature = request.data.get('signature')
        client_pubkey = request.data.get('client_pubkey')
        print("ValidateAccountView: Payload:", payload, signature, client_pubkey)
        if not (payload and signature and client_pubkey):
            print("ValidateAccountView: Missing cryptographic fields.")
            return Response({'error': 'Missing cryptographic fields.'}, status=status.HTTP_400_BAD_REQUEST)
        if not CryptoUtils.verify_signature(client_pubkey, payload.encode(), signature):
            print("ValidateAccountView: Invalid signature.")
            return Response({'error': 'Invalid signature.'}, status=status.HTTP_401_UNAUTHORIZED)
        session_key = CryptoUtils.derive_session_key(CryptoUtils.get_server_private_key(), client_pubkey)
        try:
            decrypted = CryptoUtils.decrypt(payload, session_key)
            print("ValidateAccountView: Decrypted payload:", decrypted)
            data = json.loads(decrypted.decode())
            account_number = data.get('account_number')
            print("ValidateAccountView: Account number:", account_number)
            if not account_number:
                print("ValidateAccountView: Account number is required.")
                return Response({'error': 'Account number is required.'}, status=status.HTTP_400_BAD_REQUEST)
                account = BankAccount.objects.select_related('user', 'user__profile').get(account_number=account_number)
            print("ValidateAccountView: Found account for user:", account.user.username)
            user_profile = UserProfileSerializer(account.user.profile).data
            resp = {'user': user_profile}
            encrypted = CryptoUtils.encrypt(json.dumps(resp).encode(), session_key)
            resp_signature = CryptoUtils.sign_message(CryptoUtils.get_server_private_key(), encrypted.encode())
            print("ValidateAccountView: Sending encrypted response.")
            return Response({
                'payload': encrypted,
                'signature': resp_signature,
                'server_pubkey': CryptoUtils.get_server_public_key()
            }, status=status.HTTP_200_OK)
        except BankAccount.DoesNotExist:
            print("ValidateAccountView: Account not found.")
            return Response({'error': 'Account not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print("ValidateAccountView: Exception:", str(e))
            return Response({'error': f'Failed to process request: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

class TransferView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("TransferView: Received data:", request.data)
        payload = request.data.get('payload')
        signature = request.data.get('signature')
        client_pubkey = request.data.get('client_pubkey')
        if not (payload and signature and client_pubkey):
            print("TransferView: Missing cryptographic fields.")
            return Response({'error': 'Missing cryptographic fields.'}, status=status.HTTP_400_BAD_REQUEST)
        if not CryptoUtils.verify_signature(client_pubkey, payload.encode(), signature):
            print("TransferView: Invalid signature.")
            return Response({'error': 'Invalid signature.'}, status=status.HTTP_401_UNAUTHORIZED)
        session_key = CryptoUtils.derive_session_key(CryptoUtils.get_server_private_key(), client_pubkey)
        try:
            decrypted = CryptoUtils.decrypt(payload, session_key)
            print("TransferView: Decrypted payload:", decrypted)
            data = json.loads(decrypted.decode())
            serializer = TransferSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            sender_account = serializer.validated_data['source_account']
            recipient_account = serializer.validated_data['destination_account']
            amount = serializer.validated_data['amount']
            print(f"TransferView: Sender: {sender_account.account_number}, Recipient: {recipient_account.account_number}, Amount: {amount}")
            with transaction.atomic():
                sender_account.balance -= amount
                recipient_account.balance += amount
                sender_account.save()
                recipient_account.save()
                Transaction.objects.create(
                    account=sender_account,
                    amount=-amount,
                    transaction_type='DEBIT',
                    status='COMPLETED'
                )
                Transaction.objects.create(
                    account=recipient_account,
                    amount=amount,
                    transaction_type='CREDIT',
                    status='COMPLETED'
                )
            resp = {'status': 'success', 'source_account_balance': sender_account.balance}
            encrypted = CryptoUtils.encrypt(json.dumps(resp).encode(), session_key)
            resp_signature = CryptoUtils.sign_message(CryptoUtils.get_server_private_key(), encrypted.encode())
            print("TransferView: Sending encrypted response.")
            return Response({
                'payload': encrypted,
                'signature': resp_signature,
                'server_pubkey': CryptoUtils.get_server_public_key()
            }, status=status.HTTP_200_OK)
        except Exception as e:
            print("TransferView: Exception:", str(e))
            return Response({'error': f'Transfer error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)