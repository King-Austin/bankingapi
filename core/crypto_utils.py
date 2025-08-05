import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidSignature
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import ApiKeyPair

User = get_user_model()

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
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'secure-session'
        ).derive(shared)

    @staticmethod
    def encrypt(plaintext, session_key):
        aesgcm = AESGCM(session_key)
        nonce = AESGCM.generate_key(bit_length=96)
        ct = aesgcm.encrypt(nonce, plaintext, None)
        return base64.b64encode(nonce + ct).decode()

    @staticmethod
    def decrypt(ciphertext_b64, session_key):
        data = base64.b64decode(ciphertext_b64)
        nonce, ct = data[:12], data[12:]
        aesgcm = AESGCM(session_key)
        return aesgcm.decrypt(nonce, ct, None)

    @staticmethod
    def get_user_by_public_key(public_key_pem):
        return User.objects.filter(public_key=public_key_pem).first()

    @staticmethod
    def get_or_create_server_keypair():
        keypair = ApiKeyPair.objects.filter(label="active").first()
        if not keypair:
            # Generate new P-384 key pair
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
