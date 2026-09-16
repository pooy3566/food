import uuid

import pytest
import requests


# 这个文件里的接口检查属于完整回归测试
pytestmark = pytest.mark.regression


def test_health_check(base_url):
    # 健康检查接口返回 True，说明服务已经正常启动
    response = requests.get(f"{base_url}/api/v1/utils/health-check/", timeout=5)

    assert response.status_code == 200
    assert response.json() is True


def test_health_check_responds_within_two_seconds(base_url):
    # 服务不仅要返回正确结果，还应该在合理时间内完成响应
    response = requests.get(f"{base_url}/api/v1/utils/health-check/", timeout=5)

    # elapsed 是本次请求耗时，超过 2 秒就认为响应太慢
    assert response.elapsed.total_seconds() < 2


def test_health_check_allows_local_frontend_origin(base_url):
    # 正常响应也要带 CORS 请求头，浏览器才能把结果交给前端页面
    response = requests.get(
        f"{base_url}/api/v1/utils/health-check/",
        headers={"Origin": "http://localhost:5173"},
        timeout=5,
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_health_check_returns_given_request_id(base_url):
    # 客户端传入的请求编号应该原样出现在响应中，方便追踪同一次请求
    request_id = "health-check-trace-001"
    response = requests.get(
        f"{base_url}/api/v1/utils/health-check/",
        headers={"X-Request-ID": request_id},
        timeout=5,
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_unknown_endpoint_returns_not_found(base_url):
    # 不存在的地址要返回统一的 JSON 错误回执
    response = requests.get(f"{base_url}/api/v1/does-not-exist/", timeout=5)
    result = response.json()

    assert response.status_code == 404
    assert response.headers["Content-Type"].startswith("application/json")
    assert result["detail"] == "Not found"


def test_error_response_generates_request_id(base_url):
    # 即使访问错误地址，响应也应该给出可用于查日志的请求编号
    response = requests.get(f"{base_url}/api/v1/does-not-exist/", timeout=5)
    request_id = response.headers["X-Request-ID"]

    assert response.status_code == 404
    assert uuid.UUID(request_id)
