"""真实服务的核心链路检查。"""

import pytest
import requests

from conftest import API_PREFIX, TEST_PASSWORD


pytestmark = pytest.mark.smoke


def test_health_check(base_url):
    # 像先确认商场有没有开门：接口服务必须先能正常响应。
    response = requests.get(
        f"{base_url}{API_PREFIX}/utils/health-check/", timeout=10
    )

    assert response.status_code == 200
    assert response.json() is True


def test_registered_user_can_log_in(base_url, test_user):
    # 用刚注册的账号登录，确认账号、密码和发 Token 的完整链路可用。
    response = requests.post(
        f"{base_url}{API_PREFIX}/login/access-token",
        data={"username": test_user["email"], "password": TEST_PASSWORD},
        timeout=10,
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"


def test_wrong_password_is_rejected(base_url, test_user):
    # 密码错误时不能拿到通行证，接口需要给出明确的失败结果。
    response = requests.post(
        f"{base_url}{API_PREFIX}/login/access-token",
        data={"username": test_user["email"], "password": "wrong-password"},
        timeout=10,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect email or password"


def test_token_can_access_current_user(base_url, auth_headers, test_user):
    # 带 Token 访问“当前用户”接口，确认它确实代表刚登录的账号。
    response = requests.get(
        f"{base_url}{API_PREFIX}/users/me", headers=auth_headers, timeout=10
    )

    assert response.status_code == 200
    assert response.json()["id"] == test_user["id"]
    assert response.json()["email"] == test_user["email"]
