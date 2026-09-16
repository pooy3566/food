"""真实用户资料和密码接口测试。"""

import time

import pytest
import requests

from conftest import API_PREFIX, TEST_PASSWORD


pytestmark = pytest.mark.regression


def test_user_can_update_own_profile(base_url, auth_headers, test_user):
    # 登录用户可以修改自己的姓名，返回结果应立即反映新值。
    new_name = f"修改后的测试用户-{int(time.time())}"
    response = requests.patch(
        f"{base_url}{API_PREFIX}/users/me",
        headers=auth_headers,
        json={"full_name": new_name},
        timeout=10,
    )

    assert response.status_code == 200
    assert response.json()["id"] == test_user["id"]
    assert response.json()["full_name"] == new_name


def test_profile_endpoint_requires_token(base_url):
    # 没有 Token 时不能读取当前用户资料。
    response = requests.get(f"{base_url}{API_PREFIX}/users/me", timeout=10)

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_user_can_change_password(base_url, auth_headers, test_user):
    # 先用旧密码修改，再用新密码登录，验证密码确实已经更新。
    new_password = "QaAutoTestNew2026"
    change_response = requests.patch(
        f"{base_url}{API_PREFIX}/users/me/password",
        headers=auth_headers,
        json={"current_password": TEST_PASSWORD, "new_password": new_password},
        timeout=10,
    )
    login_response = requests.post(
        f"{base_url}{API_PREFIX}/login/access-token",
        data={"username": test_user["email"], "password": new_password},
        timeout=10,
    )

    assert change_response.status_code == 200
    assert change_response.json()["message"] == "Password updated successfully"
    assert login_response.status_code == 200
    assert login_response.json()["access_token"]


def test_wrong_current_password_cannot_change_password(
    base_url, auth_headers
):
    # 当前密码不正确时，服务不能允许修改密码。
    response = requests.patch(
        f"{base_url}{API_PREFIX}/users/me/password",
        headers=auth_headers,
        json={
            "current_password": "wrong-password",
            "new_password": "QaAutoTestNew2026",
        },
        timeout=10,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect password"


def test_same_password_is_rejected(base_url, auth_headers):
    # 新旧密码相同没有实际意义，接口应拒绝这种请求。
    response = requests.patch(
        f"{base_url}{API_PREFIX}/users/me/password",
        headers=auth_headers,
        json={"current_password": TEST_PASSWORD, "new_password": TEST_PASSWORD},
        timeout=10,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "New password cannot be the same as the current one"
    )
