"""真实注册接口的输入校验测试。"""

import uuid

import pytest
import requests

from conftest import API_PREFIX, TEST_PASSWORD


pytestmark = pytest.mark.regression


def test_register_response_does_not_expose_password(base_url, admin_headers):
    # 注册成功后只能返回公开资料，不能把用户密码返回给客户端。
    email = f"qa-register-{uuid.uuid4().hex[:8]}@example.com"
    response = requests.post(
        f"{base_url}{API_PREFIX}/users/signup",
        json={"email": email, "password": TEST_PASSWORD, "full_name": "注册返回值测试"},
        timeout=10,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == email
    assert "password" not in body
    assert "hashed_password" not in body

    # 注册接口不要求登录，测试结束后用管理员账号删除临时用户。
    cleanup_response = requests.delete(
        f"{base_url}{API_PREFIX}/users/{body['id']}",
        headers=admin_headers,
        timeout=10,
    )
    assert cleanup_response.status_code == 200, cleanup_response.text


def test_register_duplicate_email_is_rejected(base_url, test_user):
    # 同一个邮箱不能重复注册，避免覆盖已有账号。
    response = requests.post(
        f"{base_url}{API_PREFIX}/users/signup",
        json={
            "email": test_user["email"],
            "password": TEST_PASSWORD,
            "full_name": "重复邮箱",
        },
        timeout=10,
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.parametrize(
    ("payload", "field_name"),
    [
        ({"email": "not-an-email", "password": TEST_PASSWORD}, "email"),
        ({"email": "qa-short-password@example.com", "password": "1234567"}, "password"),
    ],
)
def test_register_invalid_field_is_rejected(base_url, payload, field_name):
    # 邮箱格式或密码长度不符合模型要求时，接口返回 422 参数校验错误。
    response = requests.post(
        f"{base_url}{API_PREFIX}/users/signup",
        json=payload,
        timeout=10,
    )

    assert response.status_code == 422
    error_fields = {error["loc"][-1] for error in response.json()["detail"]}
    assert field_name in error_fields
