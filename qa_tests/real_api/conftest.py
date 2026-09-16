"""真实 FastAPI 服务的公共测试准备。"""

import os
import time
import uuid

import pytest
import requests


API_PREFIX = "/api/v1"
TEST_PASSWORD = "QaAutoTest2026"
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "changethis")


@pytest.fixture
def base_url():
    # 支持通过环境变量切换环境，默认连接本机 Docker 服务。
    return os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


@pytest.fixture
def admin_headers(base_url):
    # 管理员接口都需要 Token，统一在这里登录一次。
    login_response = requests.post(
        f"{base_url}{API_PREFIX}/login/access-token",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user(base_url):
    # 每条测试使用独立账号，避免相互影响，也不会使用管理员账号。
    email = f"qa-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}@example.com"
    register_response = requests.post(
        f"{base_url}{API_PREFIX}/users/signup",
        json={
            "email": email,
            "password": TEST_PASSWORD,
            "full_name": "QA 自动化测试账号",
        },
        timeout=10,
    )
    assert register_response.status_code == 200, register_response.text

    login_response = requests.post(
        f"{base_url}{API_PREFIX}/login/access-token",
        data={"username": email, "password": TEST_PASSWORD},
        timeout=10,
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    user = register_response.json()
    user["headers"] = {"Authorization": f"Bearer {token}"}

    yield user

    # 清理临时账号。服务会同时删除该账号创建的物品。
    cleanup_response = requests.delete(
        f"{base_url}{API_PREFIX}/users/me",
        headers=user["headers"],
        timeout=10,
    )
    if cleanup_response.status_code not in (200, 404):
        cleanup_response.raise_for_status()


@pytest.fixture
def auth_headers(test_user):
    # 受保护接口统一从这里拿登录凭证。
    return test_user["headers"]


@pytest.fixture
def second_user(base_url):
    # 权限测试需要第二个普通账号，验证用户之间不能互相操作数据。
    email = f"qa-second-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}@example.com"
    register_response = requests.post(
        f"{base_url}{API_PREFIX}/users/signup",
        json={"email": email, "password": TEST_PASSWORD, "full_name": "第二个测试账号"},
        timeout=10,
    )
    assert register_response.status_code == 200, register_response.text

    login_response = requests.post(
        f"{base_url}{API_PREFIX}/login/access-token",
        data={"username": email, "password": TEST_PASSWORD},
        timeout=10,
    )
    assert login_response.status_code == 200, login_response.text
    user = register_response.json()
    user["headers"] = {
        "Authorization": f"Bearer {login_response.json()['access_token']}"
    }

    yield user

    cleanup_response = requests.delete(
        f"{base_url}{API_PREFIX}/users/me",
        headers=user["headers"],
        timeout=10,
    )
    if cleanup_response.status_code not in (200, 404):
        cleanup_response.raise_for_status()


@pytest.fixture
def created_item(base_url, auth_headers):
    # 先创建一条数据，供查询、修改和删除场景使用。
    response = requests.post(
        f"{base_url}{API_PREFIX}/items/",
        headers=auth_headers,
        json={"title": "QA 临时物品", "description": "由 fixture 创建"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    item = response.json()

    yield item

    # 测试没有主动删除时，在这里兜底清理。
    cleanup_response = requests.delete(
        f"{base_url}{API_PREFIX}/items/{item['id']}",
        headers=auth_headers,
        timeout=10,
    )
    if cleanup_response.status_code not in (200, 404):
        cleanup_response.raise_for_status()
