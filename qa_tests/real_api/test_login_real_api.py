"""真实登录接口的异常输入和账号状态测试。"""

import uuid

import pytest
import requests

from conftest import API_PREFIX, TEST_PASSWORD


pytestmark = pytest.mark.regression


@pytest.fixture
def inactive_user(base_url, admin_headers):
    # 先由管理员准备一个停用账号，测试结束后再删除它。
    email = f"qa-inactive-{uuid.uuid4().hex[:8]}@example.com"
    create_response = requests.post(
        f"{base_url}{API_PREFIX}/users/",
        headers=admin_headers,
        json={
            "email": email,
            "password": TEST_PASSWORD,
            "is_active": False,
            "full_name": "停用登录测试账号",
        },
        timeout=10,
    )
    assert create_response.status_code == 200, create_response.text
    user_id = create_response.json()["id"]

    yield email

    # 无论登录断言是否通过，都把临时账号清理掉。
    delete_response = requests.delete(
        f"{base_url}{API_PREFIX}/users/{user_id}",
        headers=admin_headers,
        timeout=10,
    )
    assert delete_response.status_code in (200, 404), delete_response.text


def test_unknown_email_is_rejected(base_url):
    # 门卫找不到这个人时，不能发放通行证。
    response = requests.post(
        f"{base_url}{API_PREFIX}/login/access-token",
        data={
            "username": f"qa-unknown-{uuid.uuid4().hex[:8]}@example.com",
            "password": TEST_PASSWORD,
        },
        timeout=10,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_requires_form_fields(base_url):
    # 登录表单缺少账号或密码时，请求还没进入业务逻辑就应被参数校验拦住。
    response = requests.post(
        f"{base_url}{API_PREFIX}/login/access-token",
        data={"password": TEST_PASSWORD},
        timeout=10,
    )

    assert response.status_code == 422
    error_fields = {error["loc"][-1] for error in response.json()["detail"]}
    assert "username" in error_fields


def test_inactive_user_cannot_log_in(base_url, inactive_user):
    # 账号存在但被停用时，也不能拿到 Token。
    response = requests.post(
        f"{base_url}{API_PREFIX}/login/access-token",
        data={"username": inactive_user, "password": TEST_PASSWORD},
        timeout=10,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"


def test_failed_login_does_not_echo_password(base_url):
    # 失败响应里不能把用户提交的密码原样返回，避免敏感信息泄露。
    password = "not-safe-to-echo"
    response = requests.post(
        f"{base_url}{API_PREFIX}/login/access-token",
        data={"username": "missing@example.com", "password": password},
        timeout=10,
    )

    assert response.status_code == 400
    assert password not in response.text
