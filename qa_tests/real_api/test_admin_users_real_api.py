"""管理员用户管理接口测试。"""

import time
import uuid

import pytest
import requests

from conftest import API_PREFIX, TEST_PASSWORD


pytestmark = pytest.mark.regression


def test_normal_user_cannot_read_user_list(base_url, auth_headers):
    # 普通用户不能查看全站用户名单。
    response = requests.get(
        f"{base_url}{API_PREFIX}/users/",
        headers=auth_headers,
        timeout=10,
    )

    assert response.status_code == 403


def test_admin_can_read_user_list(base_url, admin_headers):
    # 管理员可以查看用户列表，并返回总数量和数据数组。
    response = requests.get(
        f"{base_url}{API_PREFIX}/users/",
        headers=admin_headers,
        timeout=10,
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["count"], int)
    assert isinstance(body["data"], list)


def test_admin_can_create_and_delete_user(base_url, admin_headers):
    # 管理员创建一个临时用户，确认返回信息后再删除，避免污染数据库。
    email = f"qa-admin-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}@example.com"
    create_response = requests.post(
        f"{base_url}{API_PREFIX}/users/",
        headers=admin_headers,
        json={
            "email": email,
            "password": TEST_PASSWORD,
            "full_name": "管理员创建的测试用户",
        },
        timeout=10,
    )

    assert create_response.status_code == 200, create_response.text
    created_user = create_response.json()
    assert created_user["email"] == email
    assert "password" not in created_user

    delete_response = requests.delete(
        f"{base_url}{API_PREFIX}/users/{created_user['id']}",
        headers=admin_headers,
        timeout=10,
    )
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["message"] == "User deleted successfully"


def test_normal_user_cannot_create_user(base_url, auth_headers):
    # 普通用户即使发送正确格式的数据，也不能创建其他用户。
    response = requests.post(
        f"{base_url}{API_PREFIX}/users/",
        headers=auth_headers,
        json={
            "email": f"qa-denied-{uuid.uuid4().hex[:8]}@example.com",
            "password": TEST_PASSWORD,
            "full_name": "不应创建成功",
        },
        timeout=10,
    )

    assert response.status_code == 403


def test_admin_can_update_user(base_url, admin_headers):
    # 管理员可以修改普通用户资料，修改完成后再删除临时账号。
    email = f"qa-admin-update-{uuid.uuid4().hex[:8]}@example.com"
    create_response = requests.post(
        f"{base_url}{API_PREFIX}/users/",
        headers=admin_headers,
        json={"email": email, "password": TEST_PASSWORD},
        timeout=10,
    )
    assert create_response.status_code == 200, create_response.text
    user = create_response.json()

    try:
        update_response = requests.patch(
            f"{base_url}{API_PREFIX}/users/{user['id']}",
            headers=admin_headers,
            json={"full_name": "管理员修改后的姓名"},
            timeout=10,
        )

        assert update_response.status_code == 200
        assert update_response.json()["full_name"] == "管理员修改后的姓名"
    finally:
        requests.delete(
            f"{base_url}{API_PREFIX}/users/{user['id']}",
            headers=admin_headers,
            timeout=10,
        )


def test_admin_cannot_delete_self(base_url, admin_headers):
    # 管理员不能删除自己的账号，避免系统失去最后一个管理员。
    current_response = requests.get(
        f"{base_url}{API_PREFIX}/users/me",
        headers=admin_headers,
        timeout=10,
    )
    assert current_response.status_code == 200

    delete_response = requests.delete(
        f"{base_url}{API_PREFIX}/users/{current_response.json()['id']}",
        headers=admin_headers,
        timeout=10,
    )

    assert delete_response.status_code == 403
    assert delete_response.json()["detail"] == (
        "Super users are not allowed to delete themselves"
    )


def test_user_can_read_own_user_by_id(base_url, test_user):
    # 用户可以读取自己的详情，方便前端刷新个人资料。
    response = requests.get(
        f"{base_url}{API_PREFIX}/users/{test_user['id']}",
        headers=test_user["headers"],
        timeout=10,
    )

    assert response.status_code == 200
    assert response.json()["email"] == test_user["email"]


def test_normal_user_cannot_read_other_user(base_url, test_user, second_user):
    # 普通用户不能通过用户编号查看别人的资料。
    response = requests.get(
        f"{base_url}{API_PREFIX}/users/{second_user['id']}",
        headers=test_user["headers"],
        timeout=10,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


def test_normal_user_cannot_delete_other_user(base_url, test_user, second_user):
    # 普通用户不能删除别人的账号，管理员权限不能被普通 Token 冒充。
    response = requests.delete(
        f"{base_url}{API_PREFIX}/users/{second_user['id']}",
        headers=test_user["headers"],
        timeout=10,
    )

    assert response.status_code == 403
