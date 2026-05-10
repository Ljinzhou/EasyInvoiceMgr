import os
import base64
import hashlib
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Use a dedicated key or derive from SECRET_KEY for persistence across restarts
_fernet = None


def _get_fernet() -> Fernet:
    """Lazy-init Fernet with a key derived from SECRET_KEY or a dedicated env var."""
    global _fernet
    if _fernet is not None:
        return _fernet

    key_material = os.environ.get('FERNET_KEY') or os.environ.get('SECRET_KEY') or 'easy-invoice-mgr-secret-key'
    # Derive a 32-byte URL-safe base64 key from the secret material
    digest = hashlib.sha256(key_material.encode('utf-8')).digest()
    b64_key = base64.urlsafe_b64encode(digest)
    _fernet = Fernet(b64_key)
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns base64-encoded ciphertext."""
    if not plaintext:
        return ''
    try:
        f = _get_fernet()
        token = f.encrypt(plaintext.encode('utf-8'))
        return token.decode('utf-8')
    except Exception as e:
        logger.error(f'Encryption failed: {e}')
        raise


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a previously encrypted value. Returns plaintext."""
    if not ciphertext:
        return ''
    try:
        f = _get_fernet()
        plain = f.decrypt(ciphertext.encode('utf-8'))
        return plain.decode('utf-8')
    except Exception as e:
        logger.error(f'Decryption failed: {e}')
        raise ValueError(f'Failed to decrypt value: {e}')
