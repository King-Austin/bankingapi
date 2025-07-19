import base64
import json
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key
from cryptography.exceptions import InvalidSignature
from django.conf import settings
from django.contrib.auth import get_user_model
User = get_user_model()

class CryptoUtils:
    @staticmethod
    def load_public_key(pem_data):
        return load_pem_public_key(pem_data.encode())

    @staticmethod
    def load_private_key(pem_data, password=None):
        return load_pem_private_key(pem_data.encode(), password=password)

    @staticmethod
    def verify_signature(public_key_pem, message, signature_b64):
        public_key = CryptoUtils.load_public_key(public_key_pem)
        signature = base64.b64decode(signature_b64)
        try:
            public_key.verify(
                signature,
                message,
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except InvalidSignature:
            return False

    @staticmethod
    def sign_message(private_key_pem, message):
        private_key = CryptoUtils.load_private_key(private_key_pem)
        signature = private_key.sign(
            message,
            ec.ECDSA(hashes.SHA256())
        )
        return base64.b64encode(signature).decode()

    @staticmethod
    def derive_session_key(private_key_pem, peer_public_key_pem):
        private_key = CryptoUtils.load_private_key(private_key_pem)
        peer_public_key = CryptoUtils.load_public_key(peer_public_key_pem)
        shared_key = private_key.exchange(ec.ECDH(), peer_public_key)
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'secure-session',
        ).derive(shared_key)
        return derived_key

    @staticmethod
    def encrypt(plaintext, session_key):
        aesgcm = AESGCM(session_key)
        nonce = AESGCM.generate_key(bit_length=96)
        ct = aesgcm.encrypt(nonce, plaintext, None)
        return base64.b64encode(nonce + ct).decode()

    @staticmethod
    def decrypt(ciphertext_b64, session_key):
        data = base64.b64decode(ciphertext_b64)
        nonce = data[:12]
        ct = data[12:]
        aesgcm = AESGCM(session_key)
        return aesgcm.decrypt(nonce, ct, None)

    @staticmethod
    def get_user_by_public_key(public_key_pem):
        try:
            return User.objects.get(public_key=public_key_pem)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_server_private_key():
        # Load from settings or secure storage
        return settings.SERVER_PRIVATE_KEY

    @staticmethod
    def get_server_public_key():
        return settings.SERVER_PUBLIC_KEY
