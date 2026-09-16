import pytest
import requests


@pytest.mark.smoke
def test_smoke_health_check(base_url):
    # 冒烟测试先确认服务能正常响应
    response = requests.get(f"{base_url}/api/v1/utils/health-check/", timeout=5)

    assert response.status_code == 200
    assert response.json() is True


@pytest.mark.smoke
def test_smoke_login(base_url):
    # 服务启动后先验证登录功能，后续接口都依赖它
    response = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": "admin@example.com", "password": "changethis"},
        timeout=5,
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.smoke
def test_smoke_protected_endpoint(base_url, auth_headers):
    # 再带着登录凭证访问受保护接口，确认权限链路也能工作
    response = requests.post(
        f"{base_url}/api/v1/login/test-token",
        headers=auth_headers,
        timeout=5,
    )

    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"
