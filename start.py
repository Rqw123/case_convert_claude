#!/usr/bin/env python3
"""
一键启动脚本 — 自然语言测试用例信号匹配工具
用法: python start.py [--port 8000] [--api-key sk-xxx]
"""
import argparse
import os
import subprocess
import sys
import socket
import webbrowser
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "backend")
FRONTEND_DIR = os.path.join(SCRIPT_DIR, "frontend")
SERVER_SCRIPT = os.path.join(BACKEND_DIR, "server.py")


def check_port(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) != 0


def main():
    parser = argparse.ArgumentParser(description="启动信号匹配工具")
    parser.add_argument("--port", type=int, default=8000, help="服务端口 (默认 8000)")
    parser.add_argument("--api-key", type=str, default="", help="DeepSeek API Key")
    parser.add_argument("--model", type=str, default="deepseek-chat", help="模型名称")
    parser.add_argument("--base-url", type=str, default="https://api.deepseek.com", help="API Base URL")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    port = args.port
    if not check_port(port):
        print(f"⚠  端口 {port} 已被占用，尝试 {port+1}")
        port += 1

    env = os.environ.copy()
    env["PORT"] = str(port)
    env["FRONTEND_DIR"] = FRONTEND_DIR
    env["DB_PATH"] = os.path.join(BACKEND_DIR, "case_convert.db")
    env["UPLOAD_DIR"] = os.path.join(BACKEND_DIR, "uploads")
    os.makedirs(env["UPLOAD_DIR"], exist_ok=True)

    if args.api_key:
        env["DEEPSEEK_API_KEY"] = args.api_key
    elif "DEEPSEEK_API_KEY" not in env:
        # Try to read from .env file
        env_file = os.path.join(BACKEND_DIR, ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DEEPSEEK_API_KEY="):
                        env["DEEPSEEK_API_KEY"] = line.split("=", 1)[1].strip()
                        break

    if args.model:
        env["DEEPSEEK_MODEL"] = args.model
    if args.base_url:
        env["DEEPSEEK_BASE_URL"] = args.base_url

    url = f"http://localhost:{port}"
    print("=" * 60)
    print("  🚗 自然语言测试用例信号匹配工具")
    print("=" * 60)
    print(f"  服务地址: {url}")
    print(f"  数据库  : {env['DB_PATH']}")
    print(f"  API Key : {'已配置 ✅' if env.get('DEEPSEEK_API_KEY','sk-placeholder') != 'sk-placeholder' else '未配置 ⚠ (请通过 --api-key 或 .env 文件配置)'}")
    print(f"  模型    : {env.get('DEEPSEEK_MODEL', 'deepseek-chat')}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 60)

    if not args.no_browser:
        def open_browser():
            time.sleep(1.5)
            webbrowser.open(url)
        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    os.chdir(BACKEND_DIR)
    venv_python = os.path.join(SCRIPT_DIR, ".venv", "Scripts", "python.exe")
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable
    venv_python = os.path.join(SCRIPT_DIR, ".venv", "Scripts", "python.exe")
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable                                             
    proc = subprocess.Popen([python_exe, SERVER_SCRIPT], env=env)
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n⏹  正在停止服务...")
        proc.terminate()
        proc.wait()
        print("✅ 服务已停止")


if __name__ == "__main__":
    main()
