import logging
from pathlib import Path


def configure_logging():
    # 日志文件和测试报告放在同一个目录，方便统一查看
    reports_dir = Path(__file__).resolve().parent / "reports"
    reports_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("qa_tests")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # pytest 会重复加载配置时，不再重复添加日志处理器
    if logger.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(
        reports_dir / "test.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
