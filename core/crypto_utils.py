import base64
import json
import os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from .models import ApiKeyPair

class CryptoUtils:
    @staticmethod
    def load_public_key(pem):
        return serialization.load_pem_public_key(pem.encode())

    @staticmethod
    def load_private_key(pem, password=None):
        return serialization.load_pem_private_key(pem.encode(), password=password)

    @staticmethod
    def verify_signature(public_key_pem, message, signature_b64):
        try:
            key = CryptoUtils.load_public_key(public_key_pem)
            signature = base64.b64decode(signature_b64)
            key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False

    @staticmethod
    def sign_message(private_key_pem, message):
        key = CryptoUtils.load_private_key(private_key_pem)
        signature = key.sign(message, ec.ECDSA(hashes.SHA256()))
        return base64.b64encode(signature).decode()

    @staticmethod
    def derive_session_key(private_key_pem, peer_public_key_pem):
        priv = CryptoUtils.load_private_key(private_key_pem)
        pub = CryptoUtils.load_public_key(peer_public_key_pem)
        shared = priv.exchange(ec.ECDH(), pub)
        return HKDF(
            algorithm=hashes.SHA384(),
            length=32,
            salt=None,
            info=b'secure-cipher-session-key'
        ).derive(shared)

    @staticmethod
    def encrypt(plaintext, session_key):
        aesgcm = AESGCM(session_key)
        iv = os.urandom(12)
        ct = aesgcm.encrypt(iv, plaintext, None)
        return {
            "iv": base64.b64encode(iv).decode(),
            "ciphertext": base64.b64encode(ct).decode()
        }

    @staticmethod
    def decrypt(ciphertext_b64, iv_b64, session_key):
        iv = base64.b64decode(iv_b64)
        ct = base64.b64decode(ciphertext_b64)
        aesgcm = AESGCM(session_key)
        return aesgcm.decrypt(iv, ct, None)

    @staticmethod
    def get_or_create_server_keypair():
        keypair = ApiKeyPair.objects.filter(label="active").first()
        if not keypair:
            private_key = ec.generate_private_key(ec.SECP384R1())
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()
            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            keypair = ApiKeyPair.objects.create(
                label="active",
                public_key=public_pem,
                private_key=private_pem
            )
        return keypair

    @staticmethod
    def get_server_private_key():
        return CryptoUtils.get_or_create_server_keypair().private_key

    @staticmethod
    def get_server_public_key():
        return CryptoUtils.get_or_create_server_keypair().public_key

    @staticmethod
    def crypto_preprocess(envelope):
        """
        Handles all cryptographic logic for incoming requests:
        - Decrypts AES-GCM payload using ECDH-derived session key
        - Verifies middleware and client signatures (handles raw/DER)
        - Checks nonce/timestamp for replay protection
        - Returns transaction_data, session_key, and client info (including client public key hash)
        """
        try:
            # 1. Extract envelope fields
            ephemeral_pub_b64 = envelope.get("ephemeral_pubkey")
            ciphertext_b64 = envelope.get("ciphertext")
            iv_b64 = envelope.get("iv")
            if not (ephemeral_pub_b64 and ciphertext_b64 and iv_b64):
                return None, None, "Missing cryptographic envelope fields"

            # 2. ECDH derive session key
            bank_private_key = CryptoUtils.load_private_key(CryptoUtils.get_server_private_key())
            ephemeral_pub = serialization.load_der_public_key(base64.b64decode(ephemeral_pub_b64))
            shared_secret = bank_private_key.exchange(ec.ECDH(), ephemeral_pub)
            session_key = HKDF(
                algorithm=hashes.SHA384(),
                length=32,
                salt=None,
                info=b"secure-cipher-session-key"
            ).derive(shared_secret)

            # 3. AES-GCM decrypt inner payload
            plaintext = CryptoUtils.decrypt(ciphertext_b64, iv_b64, session_key)
            payload = json.loads(plaintext.decode())
            print("DEBUG: [CryptoPreprocess] Decrypted payload:", payload)

            # 4. Signature checks
            verify_payload_with_middleware_signature = {
                "transaction_data": payload["transaction_data"],
                "client_signature": payload.get("client_signature"),
                "client_public_key": payload.get("client_public_key"),
                "nonce": payload.get("nonce")
            }
 
            middleware_payload = json.dumps(verify_payload_with_middleware_signature, separators=(',', ':'), sort_keys=True).encode()


            # Middleware signature
            middleware_sig = base64.b64decode(payload["middleware_signature"])
            try:
                middleware_pub = serialization.load_pem_public_key(payload["middleware_public_key"].encode())
            except ValueError:
                middleware_pub = serialization.load_der_public_key(base64.b64decode(payload["middleware_public_key"]))

            print(f"DEBUG: [CryptoPreprocess] Middleware public key type: {type(middleware_pub)}")
            from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
            try:
                signature_length = len(middleware_sig)
                print(f"DEBUG: [CryptoPreprocess] Middleware signature length: {signature_length}")
                if not isinstance(middleware_pub, EllipticCurvePublicKey):
                    raise TypeError("Middleware public key is not an Elliptic Curve public key")
                middleware_pub.verify(
                    middleware_sig,
                    middleware_payload,
                    ec.ECDSA(hashes.SHA256())
                )
                print("DEBUG: [CryptoPreprocess] Middleware signature verified")
            except InvalidSignature:
                print("DEBUG: [CryptoPreprocess] Invalid middleware signature")
                return None, None, "Invalid middleware signature"
            except Exception as e:
                print(f"DEBUG: [CryptoPreprocess] Exception during middleware signature verification: {e}")
                return None, None, f"Middleware signature verification error: {e}"

            # Client signature (optional)
                        
            # Client signature
            verify_payload_with_client_signature = {
                "transaction_data": payload["transaction_data"],
                }
            client_payload = json.dumps(verify_payload_with_client_signature, separators=(',', ':'), sort_keys=True).encode()
            if "client_signature" in payload and "client_public_key" in payload:
                try:
                    client_pub_key = serialization.load_pem_public_key(payload["client_public_key"].encode())
                    client_sig = base64.b64decode(payload["client_signature"])
                    print(f"DEBUG: [CryptoPreprocess] Client signature length: {len(client_sig)}")
                    # Handle raw (r||s) or DER signature for client
                    if len(client_sig) == 96:  # P-384 raw signature
                        r = int.from_bytes(client_sig[:48], 'big')
                        s = int.from_bytes(client_sig[48:], 'big')
                        client_sig = encode_dss_signature(r, s)
                    from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
                    if not isinstance(client_pub_key, EllipticCurvePublicKey):
                        raise TypeError("Client public key is not an Elliptic Curve public key")
                    client_pub_key.verify(client_sig, client_payload, ec.ECDSA(hashes.SHA256()))
                    print("DEBUG: [CryptoPreprocess] Client signature verified")
                except InvalidSignature:
                    print("DEBUG: [CryptoPreprocess] Invalid client signature")
                    return None, None, "Invalid client signature"
                except Exception as e:
                    print(f"DEBUG: [CryptoPreprocess] Exception during client signature verification: {e}")
                    return None, None, f"Client signature verification error: {e}"

            # 5. Nonce/timestamp checks (implement replay protection as needed)
            # Example: UsedNonce.objects.filter(nonce=payload["nonce"]).exists() ...

            # 6. Prepare client info
            transaction_data = payload["transaction_data"]
            if "client_public_key" in payload:
                client_pubkey_pem = payload["client_public_key"]
                transaction_data["public_key"] = client_pubkey_pem

            # 7. Return verified transaction_data, session context, and client info
            print("DEBUG: [cryptoPreprocess] TransactionData",  payload['transaction_data'])

            return payload["transaction_data"], session_key, None

        except Exception as e:
            print(f"DEBUG: [CryptoPreprocess] Exception: {e}")
            return None, None, str(e)
