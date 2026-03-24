"""
导出模块
负责将登录凭据导出为CSV或JSON格式
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List
from dataclasses import dataclass, asdict


@dataclass
class LoginCredential:
    """登录凭据数据类"""
    url: str
    username: str
    password: str
    date_created: str = ""
    date_last_used: str = ""


def format_chrome_timestamp(timestamp: int) -> str:
    """
    格式化Chrome时间戳

    Chrome使用Windows FILETIME格式（1601-01-01起的微秒数）

    Args:
        timestamp: Chrome时间戳

    Returns:
        格式化后的日期字符串
    """
    if not timestamp or timestamp <= 0:
        return ""

    try:
        # Chrome时间戳: 从1601-01-01起的微秒数
        # 转换为Unix时间戳
        # 1601-01-01到1970-01-01相差11644473600秒
        unix_timestamp = (timestamp / 1000000) - 11644473600
        dt = datetime.fromtimestamp(unix_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return str(timestamp)


def export_to_csv(credentials: List[LoginCredential], output_path: Path) -> None:
    """
    导出凭据到CSV文件

    Args:
        credentials: 凭据列表
        output_path: 输出文件路径
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 写入表头
        writer.writerow(['url', 'username', 'password', 'date_created', 'date_last_used'])

        # 写入数据
        for cred in credentials:
            writer.writerow([
                cred.url,
                cred.username,
                cred.password,
                cred.date_created,
                cred.date_last_used
            ])


def export_to_json(credentials: List[LoginCredential], output_path: Path) -> None:
    """
    导出凭据到JSON文件

    Args:
        credentials: 凭据列表
        output_path: 输出文件路径
    """
    data = [asdict(cred) for cred in credentials]

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def print_credentials(credentials: List[LoginCredential], show_password: bool = True) -> None:
    """
    在终端打印凭据

    Args:
        credentials: 凭据列表
        show_password: 是否显示密码
    """
    print("\n" + "=" * 100)
    print(f"{'URL':<50} {'用户名':<25} {'密码':<20}")
    print("=" * 100)

    for cred in credentials:
        url = cred.url[:48] + "..." if len(cred.url) > 50 else cred.url
        username = cred.username[:23] + "..." if len(cred.username) > 25 else cred.username
        password = cred.password if show_password else "****"

        print(f"{url:<50} {username:<25} {password:<20}")

    print("=" * 100)
    print(f"共 {len(credentials)} 条记录\n")


if __name__ == "__main__":
    # 测试导出功能
    test_credentials = [
        LoginCredential(
            url="https://example.com",
            username="user@example.com",
            password="testPassword123",
            date_created="2024-01-01 10:00:00",
            date_last_used="2024-01-15 15:30:00"
        ),
        LoginCredential(
            url="https://test.com",
            username="testuser",
            password="anotherPassword",
            date_created="2024-02-01 09:00:00"
        )
    ]

    # 测试打印
    print_credentials(test_credentials)

    # 测试导出
    output_dir = Path("/tmp/chrome_export_test")
    output_dir.mkdir(exist_ok=True)

    export_to_csv(test_credentials, output_dir / "credentials.csv")
    export_to_json(test_credentials, output_dir / "credentials.json")

    print(f"测试文件已导出到: {output_dir}")