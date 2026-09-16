import pytest
import requests


# 这个文件里的权限场景属于完整回归测试
pytestmark = pytest.mark.regression


def test_login_token_can_access_protected_endpoint(base_url, auth_headers):
    # 带上正确 Token 访问受保护接口，应该能识别当前用户
    response = requests.post(
        f"{base_url}/api/v1/login/test-token",
        headers=auth_headers,
        timeout=5,
    )

    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"
    assert response.json()["is_active"] is True


def test_protected_endpoint_rejects_invalid_token(base_url):
    # 随便伪造一个 Token，接口应该拒绝请求
    response = requests.post(
        f"{base_url}/api/v1/login/test-token",
        headers={"Authorization": "Bearer invalid-token"},
        timeout=5,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"


def test_protected_endpoint_rejects_missing_token(base_url):
    # 不带登录凭证时，受保护接口不允许访问
    response = requests.post(
        f"{base_url}/api/v1/login/test-token",
        headers={},
        timeout=5,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.parametrize(
    "authorization",
    [
        "demo-token",
        "Bearer",
        "Basic demo-token",
    ],
)
def test_protected_endpoint_rejects_malformed_authorization(base_url, authorization):
    # Token 格式不完整或认证方式错误时，也应该拒绝访问
    response = requests.post(
        f"{base_url}/api/v1/login/test-token",
        headers={"Authorization": authorization},
        timeout=5,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"
