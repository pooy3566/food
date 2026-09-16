"""真实服务的健康检查、跨域和 OpenAPI 基础契约测试。"""

import pytest
import requests

from conftest import API_PREFIX


pytestmark = pytest.mark.regression


def test_health_check_returns_json_true(base_url):
    # 像检查仓库总电源，健康接口必须快速返回 JSON true。
    response = requests.get(
        f"{base_url}{API_PREFIX}/utils/health-check/",
        timeout=10,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() is True


def test_unknown_api_path_returns_not_found(base_url):
    # 输入不存在的门牌号时，服务应返回 404，而不是 500。
    response = requests.get(
        f"{base_url}{API_PREFIX}/this-path-does-not-exist",
        timeout=10,
    )

    assert response.status_code == 404


def test_openapi_document_contains_core_routes(base_url):
    # OpenAPI 文档是接口目录，至少要包含登录、用户和物品三类核心路径。
    response = requests.get(
        f"{base_url}{API_PREFIX}/openapi.json",
        timeout=10,
    )

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert f"{API_PREFIX}/login/access-token" in paths
    assert f"{API_PREFIX}/users/" in paths
    assert f"{API_PREFIX}/items/" in paths


def test_items_endpoint_allows_local_cors_preflight(base_url):
    # 浏览器正式发请求前会先发 OPTIONS 预检，跨域配置正确才能继续访问。
    response = requests.options(
        f"{base_url}{API_PREFIX}/items/",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
        timeout=10,
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_admin_user_list_supports_limit(base_url, admin_headers):
    # 管理后台只请求一条记录时，接口返回的数据数组不能超过 limit。
    response = requests.get(
        f"{base_url}{API_PREFIX}/users/",
        headers=admin_headers,
        params={"skip": 0, "limit": 1},
        timeout=10,
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["count"], int)
    assert len(body["data"]) <= 1
