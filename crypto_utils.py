"""
Cryptographic utilities for secure data storage
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class SecureStorage:
    """Secure encryption/decryption for sensitive data"""
    
    def __init__(self):
        # Get encryption key from environment or generate one
        self.encryption_key = self._get_or_create_key()
        self.cipher = Fernet(self.encryption_key)
    
    def _get_or_create_key(self) -> bytes:
        """Get encryption key from environment or derive from session secret"""
        # Try to get from environment
        env_key = os.environ.get('ENCRYPTION_KEY')
        if env_key:
            return env_key.encode()
        
        # Derive from SESSION_SECRET (always available in Replit)
        session_secret = os.environ.get('SESSION_SECRET', 'default-dev-secret-change-in-production')
        
        # Use PBKDF2 to derive a proper encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'pocket-option-ssid-encryption',  # Static salt for deterministic key
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(session_secret.encode()))
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string
        
        Args:
            plaintext: String to encrypt
        
        Returns:
            Base64-encoded encrypted string
        """
        try:
            if not plaintext:
                return ""
            
            encrypted = self.cipher.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt encrypted string
        
        Args:
            ciphertext: Base64-encoded encrypted string
        
        Returns:
            Decrypted plaintext string
        """
        try:
            if not ciphertext:
                return ""
            
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    def secure_compare(self, a: str, b: str) -> bool:
        """
        Timing-safe string comparison
        
        Args:
            a: First string
            b: Second string
        
        Returns:
            True if strings are equal
        """
        if not a or not b:
            return a == b
        
        # Constant-time comparison
        if len(a) != len(b):
            return False
        
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        
        return result == 0


# Global instance
secure_storage = SecureStorage()


def encrypt_ssid(ssid: str) -> str:
    """Encrypt SSID for storage"""
    return secure_storage.encrypt(ssid)


def decrypt_ssid(encrypted_ssid: str) -> str:
    """Decrypt SSID from storage"""
    return secure_storage.decrypt(encrypted_ssid)
