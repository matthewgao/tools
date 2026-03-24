#!/usr/bin/env python3
"""
Chrome Login Data Reader - 主程序入口

提取Chrome浏览器保存的登录凭据并导出为CSV或JSON格式

用法:
    python main.py                    # 打印所有凭据
    python main.py -o credentials.csv # 导出到CSV
    python main.py -o creds.json -f json  # 导出到JSON
    python main.py --hide-password    # 隐藏密码显示
    python main.py -s aliyun          # 搜索包含"aliyun"的凭据
"""

import argparse
import sys
from pathlib import Path

from db import get_chrome_login_data_path, copy_db_to_temp, read_logins, LoginEntry
from crypto import get_decryption_key, decrypt_password
from export import LoginCredential, export_to_csv, export_to_json, print_credentials, format_chrome_timestamp


def extract_credentials(hide_password: bool = False, search: str = "") -> list[LoginCredential]:
    """
    提取Chrome登录凭据

    Args:
        hide_password: 是否隐藏密码
        search: 搜索关键词（过滤URL和用户名）

    Returns:
        凭据列表
    """
    # 检查数据库文件
    chrome_path = get_chrome_login_data_path()
    if not chrome_path.exists():
        print(f"错误: 找不到Chrome Login Data文件")
        print(f"期望路径: {chrome_path}")
        sys.exit(1)

    # 复制数据库到临时位置
    print("正在读取Chrome数据库...")
    temp_path = copy_db_to_temp(chrome_path)

    # 读取登录记录
    entries = read_logins(temp_path)
    print(f"读取到 {len(entries)} 条登录记录")

    # 获取解密密钥
    print("正在获取解密密钥...")
    try:
        aes_key = get_decryption_key()
    except Exception as e:
        print(f"错误: 无法获取解密密钥 - {e}")
        sys.exit(1)

    # 解密密码
    print("正在解密密码...")
    credentials = []

    for entry in entries:
        # 过滤
        if search:
            if search.lower() not in entry.origin_url.lower() and search.lower() not in entry.username.lower():
                continue

        # 解密密码
        password = decrypt_password(entry.encrypted_password, aes_key)

        # 创建凭据对象
        cred = LoginCredential(
            url=entry.origin_url,
            username=entry.username,
            password=password if not hide_password else "****",
            date_created=format_chrome_timestamp(entry.date_created) if entry.date_created else "",
            date_last_used=format_chrome_timestamp(entry.date_last_used) if entry.date_last_used else ""
        )
        credentials.append(cred)

    return credentials


def main():
    parser = argparse.ArgumentParser(
        description="提取Chrome浏览器保存的登录凭据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    %(prog)s                        # 打印所有凭据
    %(prog)s -o creds.csv           # 导出到CSV文件
    %(prog)s -o creds.json -f json  # 导出到JSON文件
    %(prog)s --hide-password        # 打印时隐藏密码
    %(prog)s -s google              # 搜索包含"google"的凭据
        """
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        help='输出文件路径（自动根据扩展名判断格式，或使用-f指定）'
    )

    parser.add_argument(
        '-f', '--format',
        type=str,
        choices=['csv', 'json'],
        help='输出格式（csv或json）'
    )

    parser.add_argument(
        '--hide-password',
        action='store_true',
        help='隐藏密码显示'
    )

    parser.add_argument(
        '-s', '--search',
        type=str,
        default='',
        help='搜索关键词（过滤URL和用户名）'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='限制输出数量（0表示不限制）'
    )

    args = parser.parse_args()

    # 提取凭据
    credentials = extract_credentials(hide_password=args.hide_password, search=args.search)

    # 限制数量
    if args.limit > 0:
        credentials = credentials[:args.limit]

    # 输出
    if args.output:
        output_path = Path(args.output)

        # 确定格式
        if args.format:
            fmt = args.format
        elif output_path.suffix.lower() == '.json':
            fmt = 'json'
        else:
            fmt = 'csv'

        # 导出
        if fmt == 'json':
            export_to_json(credentials, output_path)
        else:
            export_to_csv(credentials, output_path)

        print(f"已导出 {len(credentials)} 条凭据到: {output_path}")
    else:
        # 打印到终端
        print_credentials(credentials, show_password=not args.hide_password)


if __name__ == "__main__":
    main()