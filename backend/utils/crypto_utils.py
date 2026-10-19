import os
import base64
import hashlib
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# 使用专用密钥，或从 SECRET_KEY 派生，以便重启后仍可持久使用
_fernet = None


def _get_fernet() -> Fernet:
    """使用由 SECRET_KEY 或专用环境变量派生的密钥惰性初始化 Fernet。"""
    global _fernet
    if _fernet is not None:
        return _fernet

    key_material = os.environ.get('FERNET_KEY') or os.environ.get('SECRET_KEY') or 'easy-invoice-mgr-secret-key'
    # 从密钥材料派生 32 字节、URL 安全的 base64 密钥
    digest = hashlib.sha256(key_material.encode('utf-8')).digest()
    b64_key = base64.urlsafe_b64encode(digest)
    _fernet = Fernet(b64_key)
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """加密字符串值，返回 base64 编码的密文。"""
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
    """解密此前加密的值，返回明文。"""
    if not ciphertext:
        return ''
    try:
        f = _get_fernet()
        plain = f.decrypt(ciphertext.encode('utf-8'))
        return plain.decode('utf-8')
    except Exception as e:
        logger.error(f'Decryption failed: {e}')
        raise ValueError(f'Failed to decrypt value: {e}')
