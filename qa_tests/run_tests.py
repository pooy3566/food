import subprocess
import sys
import time
from pathlib import Path

import requests


QA_TESTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = QA_TESTS_DIR.parent
REPORTS_DIR = QA_TESTS_DIR / "reports"
DEMO_SERVER_PATH = QA_TESTS_DIR / "demo_server.py"
HEALTH_CHECK_URL = "http://localhost:8000/api/v1/utils/health-check/"


def server_is_ready():
    # 服务已经启动时直接复用，不再重复占用 8000 端口
    try:
        response = requests.get(HEALTH_CHECK_URL, timeout=0.5)
        return response.status_code == 200 and response.json() is True
    except requests.RequestException:
        return False


def wait_for_server():
    # 最多等待 10 秒，避免服务启动失败后一直卡住
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if server_is_ready():
            return
        time.sleep(0.2)
    raise RuntimeError("Demo API startup timed out. Check reports/demo_server.log.")


def main():
    REPORTS_DIR.mkdir(exist_ok=True)
    server_process = None
    server_log = None

    try:
        if server_is_ready():
            print("Demo API is already running. Running tests now.", flush=True)
        else:
            # 服务输出写入日志文件，方便服务启动失败时排查
            print("Starting demo API...", flush=True)
            server_log = (REPORTS_DIR / "demo_server.log").open("w", encoding="utf-8")
            server_process = subprocess.Popen(
                [sys.executable, str(DEMO_SERVER_PATH)],
                cwd=QA_TESTS_DIR,
                stdout=server_log,
                stderr=subprocess.STDOUT,
            )
            wait_for_server()
            print("Demo API is ready. Running tests now.", flush=True)

        # 一次生成终端结果、JUnit 报告和浏览器可打开的 HTML 报告
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--junitxml=qa_tests/reports/junit.xml",
            "--html=qa_tests/reports/report.html",
            "--self-contained-html",
        ]
        return subprocess.run(command, cwd=PROJECT_DIR, check=False).returncode
    finally:
        # 只停止脚本自己启动的服务，不影响用户手动启动的服务
        if server_process is not None:
            server_process.terminate()
            try:
                server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_process.kill()
        if server_log is not None:
            server_log.close()


if __name__ == "__main__":
    raise SystemExit(main())
