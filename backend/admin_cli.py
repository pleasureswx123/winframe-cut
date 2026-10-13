"""通过服务端交互初始化管理员，无默认账号或密码。"""
import argparse
import getpass
import os
from .auth import Registration, create_user


def main():
    parser = argparse.ArgumentParser(description='创建窗序管理员')
    parser.add_argument('username')
    parser.add_argument('--name', default='平台管理员')
    args = parser.parse_args()
    password = os.getenv('WINFRAME_ADMIN_PASSWORD') or getpass.getpass('管理员密码（至少 10 位）：')
    user = create_user(Registration(username=args.username, password=password, display_name=args.name), role='admin')
    print(f'管理员已创建：{user.username}')


if __name__ == '__main__':
    main()
