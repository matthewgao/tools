"""
密码解密模块
负责解密Chrome存储的加密密码

macOS上的解密流程：
1. 从Keychain获取"Chrome Safe Storage"密码
2. 使用PBKDF2派生AES密钥（salt="saltysalt", iterations=1003）
3. 使用AES-CBC with space IV解密v10格式的密码
"""

import subprocess
import base64
from pathlib import Path
from typing import Optional


def get_keychain_password() -> str:
    """
    从macOS Keychain获取Chrome Safe Storage密码

    Returns:
        Chrome Safe Storage密码字符串
    """
    result = subprocess.run(
        ['security', 'find-generic-password',
         '-a', 'Chrome',
         '-s', 'Chrome Safe Storage',
         '-w'],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"无法从Keychain获取Chrome Safe Storage: {result.stderr}")

    return result.stdout.strip()


def derive_aes_key(keychain_password: str) -> bytes:
    """
    使用PBKDF2从Keychain密码派生AES密钥

    Chrome使用的PBKDF2参数：
    - salt: "saltysalt"
    - iterations: 1003
    - key_length: 16 bytes (AES-128)

    Args:
        keychain_password: 从Keychain获取的密码

    Returns:
        派生的AES密钥
    """
    from Crypto.Protocol.KDF import PBKDF2

    salt = b'saltysalt'
    iterations = 1003

    key = PBKDF2(keychain_password.encode(), salt, dkLen=16, count=iterations)
    return key


def decrypt_password(encrypted_password: bytes, aes_key: bytes) -> str:
    """
    解密单个密码

    Chrome macOS v10格式:
    - 前3字节: "v10"版本前缀
    - 剩余: AES-CBC加密的数据
    - IV: 16个空格

    Args:
        encrypted_password: 加密的密码
        aes_key: AES解密密钥

    Returns:
        解密后的密码明文
    """
    if not encrypted_password:
        return ""

    from Crypto.Cipher import AES

    # 检查版本前缀
    if encrypted_password[:3] == b'v10':
        # v10格式: 版本前缀 + AES-CBC加密数据
        encrypted_data = encrypted_password[3:]
    else:
        # 可能是旧版本或未加密
        try:
            return encrypted_password.decode('utf-8', errors='ignore')
        except Exception:
            return "[无法解码]"

    if not encrypted_data:
        return ""

    # AES-CBC解密，使用16个空格作为IV
    iv = b' ' * 16

    try:
        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted_data)

        # 移除PKCS7填充
        pad = decrypted[-1]
        if 0 < pad <= 16:
            # 验证填充
            if all(decrypted[-i] == pad for i in range(1, pad + 1)):
                decrypted = decrypted[:-pad]

        return decrypted.decode('utf-8', errors='ignore')

    except Exception as e:
        return f"[解密失败: {e}]"


def get_decryption_key() -> bytes:
    """
    获取解密密钥（完整流程）

    Returns:
        AES解密密钥
    """
    keychain_password = get_keychain_password()
    aes_key = derive_aes_key(keychain_password)
    return aes_key


if __name__ == "__main__":
    import sqlite3
    import shutil

    # 测试解密
    print("=== Chrome密码解密测试 ===\n")

    # 获取密钥
    try:
        aes_key = get_decryption_key()
        print(f"AES密钥: {aes_key.hex()}\n")
    except Exception as e:
        print(f"获取密钥失败: {e}")
        exit(1)

    # 读取数据库
    chrome_path = Path.home() / 'Library' / 'Application Support' / 'Google' / 'Chrome' / 'Default' / 'Login Data'
    temp_path = Path('/tmp/chrome_login_data_temp')
    shutil.copy2(chrome_path, temp_path)

    conn = sqlite3.connect(str(temp_path))
    cursor = conn.cursor()
    cursor.execute('''
        SELECT origin_url, username_value, password_value
        FROM logins
        WHERE username_value != "" AND LENGTH(password_value) > 20
        LIMIT 5
    ''')
    rows = cursor.fetchall()
    conn.close()

    print("解密结果:")
    print("-" * 80)
    for url, username, enc_pwd in rows:
        password = decrypt_password(enc_pwd, aes_key)
        print(f"\nURL: {url[:60]}...")
        print(f"用户名: {username}")
        print(f"密码: {password}")