import base64
from cryptography.fernet import Fernet
from flask import current_app


class CookieCipher:
    @staticmethod
    def generate_key():
        """生成密钥"""
        return Fernet.generate_key()
    
    @staticmethod
    def encrypt_value(value: str) -> str:
        """加密值"""
        try:
            # 使用 app 的 SECRET_KEY 作为加密密钥
            key = base64.urlsafe_b64encode(current_app.config['SECRET_KEY'].encode().ljust(32)[:32])
            f = Fernet(key)
            # 加密并返回 base64 编码的字符串
            return f.encrypt(value.encode()).decode()
        except Exception as e:
            print(f"Encryption error: {str(e)}")
            return value
    
    @staticmethod
    def decrypt_value(encrypted_value: str) -> str:
        """解密值"""
        try:
            # 使用相同的密钥解密
            key = base64.urlsafe_b64encode(current_app.config['SECRET_KEY'].encode().ljust(32)[:32])
            f = Fernet(key)
            # 解密并返回原始字符串
            return f.decrypt(encrypted_value.encode()).decode()
        except Exception as e:
            print(f"Decryption error: {str(e)}")
            return encrypted_value


