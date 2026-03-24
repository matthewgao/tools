"""
SQLite数据库读取模块
负责读取Chrome Login Data数据库，提取logins表数据
"""

import sqlite3
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import shutil


@dataclass
class LoginEntry:
    """登录凭据条目"""
    origin_url: str
    username: str
    encrypted_password: bytes
    date_created: Optional[int] = None
    date_last_used: Optional[int] = None


def get_chrome_login_data_path() -> Path:
    """获取Chrome Login Data数据库路径"""
    home = Path.home()
    chrome_path = home / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "Login Data"
    return chrome_path


def get_chrome_local_state_path() -> Path:
    """获取Chrome Local State文件路径"""
    home = Path.home()
    local_state_path = home / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "Local State"
    return local_state_path


def copy_db_to_temp(chrome_db_path: Path) -> Path:
    """
    复制数据库到临时位置，避免Chrome锁定问题

    Args:
        chrome_db_path: Chrome数据库原始路径

    Returns:
        临时数据库路径
    """
    temp_path = Path("/tmp") / "chrome_login_data_temp"
    shutil.copy2(chrome_db_path, temp_path)
    return temp_path


def read_logins(db_path: Path) -> list[LoginEntry]:
    """
    从数据库读取登录凭据

    Args:
        db_path: Login Data数据库路径

    Returns:
        登录凭据列表
    """
    entries = []

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 查询logins表
        cursor.execute("""
            SELECT origin_url, username_value, password_value,
                   date_created, date_last_used
            FROM logins
            WHERE username_value != ''
        """)

        for row in cursor.fetchall():
            entry = LoginEntry(
                origin_url=row[0] or "",
                username=row[1] or "",
                encrypted_password=row[2] or b"",
                date_created=row[3],
                date_last_used=row[4]
            )
            entries.append(entry)

    finally:
        conn.close()

    return entries


def get_database_info(db_path: Path) -> dict:
    """
    获取数据库基本信息

    Args:
        db_path: 数据库路径

    Returns:
        数据库信息字典
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 获取表列表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # 获取logins表记录数
        cursor.execute("SELECT COUNT(*) FROM logins")
        count = cursor.fetchone()[0]

        return {
            "tables": tables,
            "logins_count": count
        }
    finally:
        conn.close()


if __name__ == "__main__":
    # 测试读取
    chrome_path = get_chrome_login_data_path()
    print(f"Chrome Login Data路径: {chrome_path}")
    print(f"文件存在: {chrome_path.exists()}")

    if chrome_path.exists():
        # 复制到临时位置
        temp_path = copy_db_to_temp(chrome_path)
        print(f"临时数据库: {temp_path}")

        # 读取数据
        info = get_database_info(temp_path)
        print(f"数据库信息: {info}")

        entries = read_logins(temp_path)
        print(f"读取到 {len(entries)} 条登录记录")

        for entry in entries[:3]:
            print(f"  - {entry.origin_url}: {entry.username}")