from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, serializers
from django.db import transaction
from .models import User, Transaction
from .serializers import (
    UserRegistrationSerializer, UserSerializer,
    TransactionSerializer, TransferSerializer
)
from .crypto_utils import CryptoUtils
import json


class PublicKeyView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        print("DEBUG: [PublicKeyView.get] Called")
        public_key = CryptoUtils.get_server_public_key()
        print(f"DEBUG: [PublicKeyView.get] public_key={public_key}")
        if not public_key:
            print("DEBUG: [PublicKeyView.get] Public key not found")
            return Response({'error': 'Public key not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'public_key': public_key}, status=status.HTTP_200_OK)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("DEBUG: [RegisterView.post] Received request data:", request.data)
        transaction_data, session_key, client_info_or_error = CryptoUtils.crypto_preprocess(request.data)
        print(f"DEBUG: [RegisterView.post] transaction_data={transaction_data}, session_key={session_key}, client_info_or_error={client_info_or_error}")

        if isinstance(client_info_or_error, str):  # Error string
            print(f"DEBUG: [RegisterView.post] Crypto error: {client_info_or_error}")
            return Response({"error": client_info_or_error}, status=400)

        transaction_data['account_number'] = transaction_data.get("phone_number").lstrip('0').replace('+234', '').replace(' ', '').replace('-', '')[:10]
        print("DEBUG: [RegisterView.post] transaction_data after account_number processing:", transaction_data)
        serializer = UserRegistrationSerializer(data=transaction_data)
        print("DEBUG: [RegisterView.post] serializer.is_valid() check")
        if not serializer.is_valid():
            print("DEBUG: [RegisterView.post] serializer.errors:", serializer.errors)
            return Response(serializer.errors, status=400)

        try:
            with transaction.atomic():
                print("DEBUG: [RegisterView.post] Saving user")
                user = serializer.save()
        except serializers.ValidationError as ve:
            print("DEBUG: [RegisterView.post] serializers.ValidationError:", ve.detail)
            return Response(ve.detail, status=400)
        except Exception as e:
            print("DEBUG: [RegisterView.post] Exception:", str(e))
            return Response({'error': str(e)}, status=500)

        print("DEBUG: [RegisterView.post] User created:", user)
        return encrypted_response(
            session_key,
            {
                'user': UserSerializer(user).data,
                'transactions': TransactionSerializer(
                    Transaction.objects.filter(account=user).order_by('-created_at'), many=True
                ).data
            }
        )


class TransferView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("DEBUG: [TransferView.post] Received request data:", request.data)
        transaction_data, session_key, error = CryptoUtils.crypto_preprocess(request.data)
        print(f"DEBUG: [TransferView.post] transaction_data={transaction_data}, session_key={session_key}, error={error}")

        if error:
            print("DEBUG: [TransferView.post] Crypto error:", error)
            return Response({"error": error}, status=400)

        serializer = TransferSerializer(data=transaction_data)
        print("DEBUG: [TransferView.post] serializer.is_valid() check")
        serializer.is_valid(raise_exception=True)

        sender = serializer.validated_data['source_account']
        recipient = serializer.validated_data['destination_account']
        amount = serializer.validated_data['amount']
        print(f"DEBUG: [TransferView.post] sender={sender}, recipient={recipient}, amount={amount}")

        try:
            with transaction.atomic():
                print("DEBUG: [TransferView.post] Updating balances")
                sender.balance -= amount
                recipient.balance += amount
                sender.save()
                recipient.save()

                print("DEBUG: [TransferView.post] Creating Transaction records")
                Transaction.objects.bulk_create([
                    Transaction(account=sender, amount=-amount, transaction_type='DEBIT', status='COMPLETED'),
                    Transaction(account=recipient, amount=amount, transaction_type='CREDIT', status='COMPLETED')
                ])

            print("DEBUG: [TransferView.post] Transfer successful")
            return encrypted_response(session_key, {
                'status': 'success',
                'source_account_balance': sender.balance
            })

        except Exception as e:
            print("DEBUG: [TransferView.post] Exception:", str(e))
            return Response({'error': f'Transfer error: {str(e)}'}, status=400)


class ValidateAccountView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("DEBUG: [ValidateAccountView.post] Received request data:", request.data)
        transaction_data, session_key, error = CryptoUtils.crypto_preprocess(request.data)
        print(f"DEBUG: [ValidateAccountView.post] transaction_data={transaction_data}, session_key={session_key}, error={error}")

        if error:
            print("DEBUG: [ValidateAccountView.post] Crypto error:", error)
            return Response({"error": error}, status=400)

        account_number = transaction_data.get('account_number')
        print(f"DEBUG: [ValidateAccountView.post] account_number={account_number}")
        if not account_number:
            print("DEBUG: [ValidateAccountView.post] Account number missing")
            return Response({'error': 'Account number is required.'}, status=400)

        try:
            print("DEBUG: [ValidateAccountView.post] Querying BankAccount")
            account = BankAccount.objects.select_related('user').get(account_number=account_number)
            user_data = UserSerializer(account.user).data
            print("DEBUG: [ValidateAccountView.post] Account found, user_data:", user_data)
            return encrypted_response(session_key, {'user': user_data})
        except BankAccount.DoesNotExist:
            print("DEBUG: [ValidateAccountView.post] Account not found")
            return Response({'error': 'Account not found.'}, status=404)
        except Exception as e:
            print("DEBUG: [ValidateAccountView.post] Exception:", str(e))
            return Response({'error': f'Validation failed: {str(e)}'}, status=400)


# Utility function for encrypted + signed responses
def encrypted_response(session_key, payload, status_code=status.HTTP_200_OK):
    print(f"DEBUG: [encrypted_response] session_key={session_key}, payload={payload}")
    try:
        plaintext = json.dumps(payload).encode()
        print("DEBUG: [encrypted_response] plaintext:", plaintext)
        encrypted = CryptoUtils.encrypt(plaintext, session_key)
        print("DEBUG: [encrypted_response] encrypted:", encrypted)
        if isinstance(encrypted, dict):
            encrypted_str = json.dumps(encrypted)
        else:
            encrypted_str = str(encrypted)
        signature = CryptoUtils.sign_message(CryptoUtils.get_server_private_key(), encrypted_str.encode())
        print("DEBUG: [encrypted_response] signature:", signature)

        return Response({
            'payload': encrypted,
            'signature': signature,
            'server_pubkey': CryptoUtils.get_server_public_key()
        }, status=status_code)

    except Exception as e:
        print("DEBUG: [encrypted_response] Failed:", str(e))
        return Response({'error': 'Encryption or signing failed'}, status=500)

