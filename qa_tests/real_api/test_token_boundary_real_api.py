"""真实 Token 认证边界测试。"""

import pytest
import requests

from conftest import API_PREFIX


pytestmark = pytest.mark.regression


def test_invalid_token_cannot_access_current_user(base_url):
    # 门卫拿到一张伪造的通行证时，必须拒绝进入受保护区域。
    response = requests.get(
        f"{base_url}{API_PREFIX}/users/me",
        headers={"Authorization": "Bearer definitely-invalid-token"},
        timeout=10,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"


def test_missing_token_cannot_call_token_check(base_url):
    # Token 检查接口本身也不能被匿名访问。
    response = requests.post(
        f"{base_url}{API_PREFIX}/login/test-token",
        timeout=10,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
