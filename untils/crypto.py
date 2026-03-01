"""
Cryptography utilities for encryption/decryption
"""

import base64
from Crypto.Cipher import AES
from typing import Union

class CryptoManager:
    def __init__(self):
        # Keys from reverse engineering
        self.main_key = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
        self.main_iv = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
        self.block_size = AES.block_size
    
    def pad(self, text: bytes) -> bytes:
        """Add PKCS7 padding"""
        padding_length = self.block_size - (len(text) % self.block_size)
        return text + bytes([padding_length] * padding_length)
    
    def unpad(self, text: bytes) -> bytes:
        """Remove PKCS7 padding"""
        padding_length = text[-1]
        return text[:-padding_length]
    
    def encrypt(self, plaintext: Union[str, bytes]) -> bytes:
        """AES CBC encrypt"""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        
        aes = AES.new(self.main_key, AES.MODE_CBC, self.main_iv)
        padded = self.pad(plaintext)
        return aes.encrypt(padded)
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """AES CBC decrypt"""
        aes = AES.new(self.main_key, AES.MODE_CBC, self.main_iv)
        decrypted = aes.decrypt(ciphertext)
        return self.unpad(decrypted)
