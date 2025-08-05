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

class get_public_key(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        print("DEBUG: [PublicKey] Fetching server public key")
        public_key = CryptoUtils.get_server_public_key()
        if not public_key:
            print("DEBUG: [PublicKey] No public key found.")
            return Response({'error': 'Public key not found.'}, status=status.HTTP_404_NOT_FOUND)
        print("DEBUG: [PublicKey] Public key retrieved successfully.")
        return Response({'public_key': public_key}, status=status.HTTP_200_OK)
    
    
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("DEBUG: [Register] Received registration data:", request.data)
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        print(f"DEBUG: [Register] Created user: {user.username}")
        accounts = BankAccount.objects.filter(user=user)
        transactions = Transaction.objects.filter(account__user=user).order_by('-created_at')
        print(f"DEBUG: [Register] Accounts found: {accounts.count()}, Transactions found: {transactions.count()}")
        return Response({
            'user': UserProfileSerializer(user.profile).data,
            'accounts': BankAccountSerializer(accounts, many=True).data,
            'transactions': TransactionSerializer(transactions, many=True).data
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("DEBUG: [Login] Received login data:", request.data)
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        print(f"DEBUG: [Login] Authenticated user: {user.username}")
        accounts = BankAccount.objects.filter(user=user)
        transactions = Transaction.objects.filter(account__user=user).order_by('-created_at')
        print(f"DEBUG: [Login] Accounts found: {accounts.count()}, Transactions found: {transactions.count()}")
        return Response({
            'user': UserProfileSerializer(user.profile).data,
            'accounts': BankAccountSerializer(accounts, many=True).data,
            'transactions': TransactionSerializer(transactions, many=True).data
        })

class ValidateAccountView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("DEBUG: [ValidateAccount] Received data:", request.data)
        payload = request.data.get('payload')
        signature = request.data.get('signature')
        client_pubkey = request.data.get('client_pubkey')
        print("DEBUG: [ValidateAccount] Payload:", payload)
        print("DEBUG: [ValidateAccount] Signature:", signature)
        print("DEBUG: [ValidateAccount] Client public key:", client_pubkey)
        if not (payload and signature and client_pubkey):
            print("DEBUG: [ValidateAccount] Missing cryptographic fields.")
            return Response({'error': 'Missing cryptographic fields.'}, status=status.HTTP_400_BAD_REQUEST)
        if not CryptoUtils.verify_signature(client_pubkey, payload.encode(), signature):
            print("DEBUG: [ValidateAccount] Invalid signature.")
            return Response({'error': 'Invalid signature.'}, status=status.HTTP_401_UNAUTHORIZED)
        print("DEBUG: [ValidateAccount] Signature verified.")
        session_key = CryptoUtils.derive_session_key(CryptoUtils.get_server_private_key(), client_pubkey)
        print("DEBUG: [ValidateAccount] Session key derived.")
        try:
            decrypted = CryptoUtils.decrypt(payload, session_key)
            print("DEBUG: [ValidateAccount] Decrypted payload:", decrypted)
            data = json.loads(decrypted.decode())
            account_number = data.get('account_number')
            print("DEBUG: [ValidateAccount] Account number:", account_number)
            if not account_number:
                print("DEBUG: [ValidateAccount] Account number is required.")
                return Response({'error': 'Account number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            account = BankAccount.objects.select_related('user', 'user__profile').get(account_number=account_number)
            print(f"DEBUG: [ValidateAccount] Found account for user: {account.user.username}")
            user_profile = UserProfileSerializer(account.user.profile).data
            resp = {'user': user_profile}
            encrypted = CryptoUtils.encrypt(json.dumps(resp).encode(), session_key)
            print("DEBUG: [ValidateAccount] Encrypted response:", encrypted)
            resp_signature = CryptoUtils.sign_message(CryptoUtils.get_server_private_key(), encrypted.encode())
            print("DEBUG: [ValidateAccount] Response signature:", resp_signature)
            print("DEBUG: [ValidateAccount] Sending encrypted response.")
            return Response({
                'payload': encrypted,
                'signature': resp_signature,
                'server_pubkey': CryptoUtils.get_server_public_key()
            }, status=status.HTTP_200_OK)
        except BankAccount.DoesNotExist:
            print("DEBUG: [ValidateAccount] Account not found.")
            return Response({'error': 'Account not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print("DEBUG: [ValidateAccount] Exception:", str(e))
            return Response({'error': f'Failed to process request: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

class TransferView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("DEBUG: [Transfer] Received data:", request.data)
        payload = request.data.get('payload')
        signature = request.data.get('signature')
        client_pubkey = request.data.get('client_pubkey')
        print("DEBUG: [Transfer] Payload:", payload)
        print("DEBUG: [Transfer] Signature:", signature)
        print("DEBUG: [Transfer] Client public key:", client_pubkey)
        if not (payload and signature and client_pubkey):
            print("DEBUG: [Transfer] Missing cryptographic fields.")
            return Response({'error': 'Missing cryptographic fields.'}, status=status.HTTP_400_BAD_REQUEST)
        if not CryptoUtils.verify_signature(client_pubkey, payload.encode(), signature):
            print("DEBUG: [Transfer] Invalid signature.")
            return Response({'error': 'Invalid signature.'}, status=status.HTTP_401_UNAUTHORIZED)
        print("DEBUG: [Transfer] Signature verified.")
        session_key = CryptoUtils.derive_session_key(CryptoUtils.get_server_private_key(), client_pubkey)
        print("DEBUG: [Transfer] Session key derived.")
        try:
            decrypted = CryptoUtils.decrypt(payload, session_key)
            print("DEBUG: [Transfer] Decrypted payload:", decrypted)
            data = json.loads(decrypted.decode())
            serializer = TransferSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            sender_account = serializer.validated_data['source_account']
            recipient_account = serializer.validated_data['destination_account']
            amount = serializer.validated_data['amount']
            print(f"DEBUG: [Transfer] Sender: {sender_account.account_number}, Recipient: {recipient_account.account_number}, Amount: {amount}")
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
            print("DEBUG: [Transfer] Encrypted response:", encrypted)
            resp_signature = CryptoUtils.sign_message(CryptoUtils.get_server_private_key(), encrypted.encode())
            print("DEBUG: [Transfer] Response signature:", resp_signature)
            print("DEBUG: [Transfer] Sending encrypted response.")
            return Response({
                'payload': encrypted,
                'signature': resp_signature,
                'server_pubkey': CryptoUtils.get_server_public_key()
            }, status=status.HTTP_200_OK)
        except Exception as e:
            print("DEBUG: [Transfer] Exception:", str(e))
            return Response({'error': f'Transfer error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
def secure_transaction(request):
    """
    Banking API endpoint:
    - Handles secure payload from middleware
    - Verifies middleware & client signatures
    - Routes transaction to business logic
    """
    try:
        # =====================
        # 1. Outer Crypto Layer
        # =====================
        # Parse envelope
        envelope = request.data
        ephemeral_pub_b64 = envelope.get("ephemeral_pubkey")
        ciphertext_b64 = envelope.get("ciphertext")
        iv_b64 = envelope.get("iv")
        if not (ephemeral_pub_b64 and ciphertext_b64 and iv_b64):
            return Response({"error": "Invalid request by the"}, status=400)

        # ECDH derive session key
        bank_private_key = load_bank_private_key()  # From DB or secure store
        ephemeral_pub = serialization.load_der_public_key(base64.b64decode(ephemeral_pub_b64))
        shared_secret = bank_private_key.exchange(ec.ECDH(), ephemeral_pub)
        session_key = HKDF(
            algorithm=hashes.SHA384(),
            length=32,
            salt=None,
            info=b"secure-cipher-session-key"
        ).derive(shared_secret)

        # AES-GCM decrypt inner payload
        aesgcm = AESGCM(session_key)
        plaintext = aesgcm.decrypt(
            base64.b64decode(iv_b64),
            base64.b64decode(ciphertext_b64),
            None
        )
        payload = json.loads(plaintext.decode())
        print("DEBUG: Decrypted payload:", payload)

        # =====================
        # 2. Signature Checks
        # =====================
        # Verify middleware signature
        middleware_sig = base64.b64decode(payload["middleware_signature"])
        middleware_pub_der = base64.b64decode(payload["middleware_public_key"])
        middleware_pub = serialization.load_der_public_key(middleware_pub_der)

        verify_payload = {
            "transaction_data": payload["transaction_data"],
            "timestamp": payload["timestamp"],
            "nonce": payload["nonce"]
        }

        message = json.dumps(verify_payload, separators=(',', ':'), sort_keys=True).encode()
        middleware_pub.verify(middleware_sig, message, ec.ECDSA(hashes.SHA256()))
        print("✅ Middleware signature verified")

        # (Optional) Verify client signature if payload includes it
        client_pub_key = serialization.load_pem_public_key(payload["client_public_key"].encode())
        client_sig = base64.b64decode(payload["client_signature"])
        client_pub_key.verify(client_sig, message, ec.ECDSA(hashes.SHA256()))
        print("✅ Client signature verified (optional)")

        # =====================
        # 3. Transaction Logic
        # =====================
        tx_data = payload["transaction_data"]
        tx_result = process_transaction(tx_data)  # Isolated function (below)

        # =====================
        # 4. Response Signing & Encryption
        # =====================
        response_payload = {
            "transaction_result": tx_result,
            "timestamp": int(time.time()),
            "nonce": payload["nonce"]
        }

        # Sign response with bank's private key
        bank_sig = bank_private_key.sign(
            json.dumps(response_payload, separators=(',', ':'), sort_keys=True).encode(),
            ec.ECDSA(hashes.SHA256())
        )
        response_payload["bank_signature"] = base64.b64encode(bank_sig).decode()
        response_payload["bank_public_key"] = export_bank_public_key()

        # Encrypt response with same session key
        response_bytes = json.dumps(response_payload, separators=(',', ':')).encode()
        resp_iv = os.urandom(12)
        resp_ciphertext = AESGCM(session_key).encrypt(resp_iv, response_bytes, None)

        return Response({
            "iv": base64.b64encode(resp_iv).decode(),
            "ciphertext": base64.b64encode(resp_ciphertext).decode()
        }, status=200)

    except Exception as e:
        print(f"❌ Secure transaction error: {e}")
        return Response({"error": str(e)}, status=400)
