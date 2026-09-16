import csv
from io import StringIO

import pytest
import requests


# 导出属于物品模块的完整回归测试
pytestmark = pytest.mark.regression


def test_authenticated_user_can_export_items_as_csv(
    base_url, auth_headers, created_items
):
    # 登录用户下载清单后，文件中应该包含刚创建的两条物品
    response = requests.get(
        f"{base_url}/api/v1/items/export",
        headers=auth_headers,
        timeout=5,
    )
    rows = list(csv.DictReader(StringIO(response.text)))
    exported_ids = {row["id"] for row in rows}

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    assert response.headers["Content-Disposition"] == 'attachment; filename="items.csv"'
    assert {item["id"] for item in created_items} <= exported_ids


def test_item_export_returns_given_request_id(base_url, auth_headers, created_item):
    # 导出文件同样应返回调用方传入的请求编号，便于排查下载记录
    response = requests.get(
        f"{base_url}/api/v1/items/export",
        headers={**auth_headers, "X-Request-ID": "export-check-001"},
        timeout=5,
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "export-check-001"
    assert created_item["id"] in response.text


def test_item_export_without_token_is_rejected(base_url):
    # 未登录用户不能导出业务数据
    response = requests.get(
        f"{base_url}/api/v1/items/export",
        headers={},
        timeout=5,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"
