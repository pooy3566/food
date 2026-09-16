import uuid

import pytest
import requests


# 这个文件里的注册场景属于完整回归测试
pytestmark = pytest.mark.regression


def test_user_can_register(base_url):
    # 每次使用不同邮箱注册，避免和之前的测试数据重复
    email = f"student-{uuid.uuid4().hex[:8]}@example.com"
    response = requests.post(
        f"{base_url}/api/v1/users/signup",
        json={"email": email, "password": "strongpass", "full_name": "Test Student"},
        timeout=5,
    )
    result = response.json()

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    assert {"email", "full_name", "is_active"} <= result.keys()
    assert result["email"] == email
    assert result["full_name"] == "Test Student"
    assert result["is_active"] is True


def test_register_response_has_expected_data_types(base_url):
    # 注册返回的数据应保持固定类型，方便前端和其他接口使用
    email = f"type-check-{uuid.uuid4().hex[:8]}@example.com"
    response = requests.post(
        f"{base_url}/api/v1/users/signup",
        json={"email": email, "password": "strongpass", "full_name": "Type Check"},
        timeout=5,
    )
    result = response.json()

    assert response.status_code == 200
    assert isinstance(result["email"], str)
    assert isinstance(result["full_name"], str)
    assert isinstance(result["is_active"], bool)


def test_register_with_invalid_json_is_rejected(base_url):
    # 注册请求正文不是合法 JSON 时，接口应该返回格式错误
    response = requests.post(
        f"{base_url}/api/v1/users/signup",
        headers={"Content-Type": "application/json"},
        data='{"email":',
        timeout=5,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid JSON"


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"email": "admin@example.com", "password": "strongpass"}, 400),
        ({"email": "new@example.com", "password": "short"}, 422),
        ({"email": "not-an-email", "password": "strongpass"}, 422),
        ({"email": "student2@example.com", "password": "1234567"}, 422),
    ],
)
def test_invalid_registration_is_rejected(base_url, payload, expected_status):
    # 检查重复邮箱、短密码和错误邮箱等输入是否被正确拦截
    response = requests.post(
        f"{base_url}/api/v1/users/signup",
        json=payload,
        timeout=5,
    )

    assert response.status_code == expected_status


def test_failed_registration_does_not_expose_password(base_url):
    # 注册失败时，错误信息不应该包含用户提交的密码
    password = "secret-short-password"
    response = requests.post(
        f"{base_url}/api/v1/users/signup",
        json={"email": "not-an-email", "password": password},
        timeout=5,
    )

    assert response.status_code == 422
    assert password not in response.text
