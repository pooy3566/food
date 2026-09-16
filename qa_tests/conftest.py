import logging
import os

import pytest
import requests

from logging_config import configure_logging


logger = logging.getLogger("qa_tests.results")


def pytest_configure(config):
    # pytest 启动时先配置日志，所有测试都可以共用
    configure_logging()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # 每条测试执行结束后，记录测试名称、结果和耗时
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        logger.info(
            "TEST %s -> %s, duration=%.2fs",
            report.nodeid,
            report.outcome.upper(),
            report.duration,
        )


@pytest.fixture
def base_url():
    # 测试服务地址可通过 BASE_URL 切换，默认使用本地服务
    return os.getenv("BASE_URL", "http://localhost:8000")


@pytest.fixture
def auth_headers(base_url):
    # 统一登录并生成请求头，后面需要权限的接口直接复用
    # 账号信息从环境变量读取，未设置时使用演示服务的默认账号
    username = os.getenv("TEST_USERNAME", "admin@example.com")
    password = os.getenv("TEST_PASSWORD", "changethis")
    login_response = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": username, "password": password},
        timeout=5,
    )
    login_response.raise_for_status()
    token = login_response.json()["access_token"]
    assert token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def created_item(base_url, auth_headers):
    # 测试开始前创建一条物品，供查询、修改和删除场景使用
    response = requests.post(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        json={"title": "Fixture 测试物品", "description": "由 fixture 创建"},
        timeout=5,
    )
    response.raise_for_status()
    item = response.json()

    # 把物品交给测试函数使用，测试结束后会继续执行下面的清理代码
    yield item

    # 删除测试产生的数据，避免多次运行后服务里留下大量无用物品
    cleanup_response = requests.delete(
        f"{base_url}/api/v1/items/{item['id']}",
        headers=auth_headers,
        timeout=5,
    )
    # 删除测试中已经删过的物品时返回 404，这种情况也算清理完成
    if cleanup_response.status_code not in (200, 404):
        cleanup_response.raise_for_status()


@pytest.fixture
def created_items(base_url, auth_headers):
    # 一次准备两条物品，专门用来验证列表翻页
    items = []
    for index in range(2):
        response = requests.post(
            f"{base_url}/api/v1/items/",
            headers=auth_headers,
            json={
                "title": f"分页测试物品 {index + 1}",
                "description": "用于测试 skip 和 limit",
            },
            timeout=5,
        )
        response.raise_for_status()
        items.append(response.json())

    # 把两条测试数据交给测试函数使用
    yield items

    # 测试结束后逐条删除，保持服务数据干净
    for item in items:
        cleanup_response = requests.delete(
            f"{base_url}/api/v1/items/{item['id']}",
            headers=auth_headers,
            timeout=5,
        )
        if cleanup_response.status_code not in (200, 404):
            cleanup_response.raise_for_status()
