"""
密码加密模块 - 用于保护交换机 SSH 凭据
使用 Fernet 对称加密，密钥来自环境变量或配置文件
"""
import os
import base64
from cryptography.fernet import Fernet, InvalidToken


def _get_key():
    """获取或生成加密密钥"""
    key = os.environ.get('IPAM_ENCRYPTION_KEY')
    if key:
        return key.encode()
    
    # 从配置文件读取（如果存在）
    key_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.encryption_key')
    if os.path.exists(key_file):
        with open(key_file, 'r') as f:
            return f.read().strip().encode()
    
    # 生成新密钥并保存
    new_key = Fernet.generate_key()
    try:
        with open(key_file, 'w') as f:
            f.write(new_key.decode())
        os.chmod(key_file, 0o600)
    except Exception:
        pass
    return new_key


def encrypt_password(password):
    """加密密码"""
    if not password:
        return ''
    f = Fernet(_get_key())
    return f.encrypt(password.encode()).decode()


def decrypt_password(encrypted):
    """解密密码"""
    if not encrypted:
        return ''
    try:
        f = Fernet(_get_key())
        return f.decrypt(encrypted.encode()).decode()
    except InvalidToken:
        return ''


def is_encrypted(value):
    """判断是否为加密值"""
    return bool(value and value.startswith('gAAAAA'))
