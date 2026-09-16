import pytest
import requests


# 这个文件里的登录场景属于完整回归测试
pytestmark = pytest.mark.regression


def test_login_success(base_url):
    # 使用正确账号登录，检查接口是否返回可用 Token
    response = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": "admin@example.com", "password": "changethis"},
        timeout=5,
    )
    # 把响应正文转成字典，后面统一检查返回字段
    result = response.json()

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    assert {"access_token", "token_type"} <= result.keys()
    assert result["token_type"] == "bearer"
    assert result["access_token"]


def test_login_response_has_expected_data_types(base_url):
    # 登录成功后，Token 和类型字段都应该是字符串
    response = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": "admin@example.com", "password": "changethis"},
        timeout=5,
    )
    result = response.json()

    assert response.status_code == 200
    assert isinstance(result["access_token"], str)
    assert isinstance(result["token_type"], str)
    assert result["access_token"].strip()


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("admin@example.com", "wrong-password"),
        ("unknown@example.com", "changethis"),
        ("admin@example.com", ""),
        ("", "changethis"),
    ],
)
def test_invalid_login_is_rejected(base_url, username, password):
    # 用多组错误输入确认登录接口会拒绝非法账号或密码
    response = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": username, "password": password},
        timeout=5,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect email or password"


def test_failed_login_does_not_expose_password(base_url):
    # 登录失败时，返回内容不应该把用户输入的密码原样带出来
    password = "private-login-password"
    response = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": "admin@example.com", "password": password},
        timeout=5,
    )

    assert response.status_code == 400
    assert password not in response.text
