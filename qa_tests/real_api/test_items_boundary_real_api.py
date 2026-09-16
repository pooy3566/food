"""真实物品接口的分页、格式和 HTTP 方法边界测试。"""

import pytest
import requests

from conftest import API_PREFIX


pytestmark = pytest.mark.regression


def _create_item(base_url, headers, title):
    # 测试需要多条数据时，统一用这个小工具创建物品。
    response = requests.post(
        f"{base_url}{API_PREFIX}/items/",
        headers=headers,
        json={"title": title, "description": "边界测试数据"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_item_list_supports_skip_and_limit(base_url, auth_headers):
    # 像仓库盘点时只取第 2 页的 1 条记录，返回数量应受 limit 控制。
    items = [_create_item(base_url, auth_headers, f"分页物品-{index}") for index in range(3)]

    try:
        response = requests.get(
            f"{base_url}{API_PREFIX}/items/",
            headers=auth_headers,
            params={"skip": 1, "limit": 1},
            timeout=10,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["count"] >= 3
        assert len(body["data"]) == 1
        assert body["data"][0]["id"] in {item["id"] for item in items}
    finally:
        for item in items:
            requests.delete(
                f"{base_url}{API_PREFIX}/items/{item['id']}",
                headers=auth_headers,
                timeout=10,
            )


@pytest.mark.parametrize("params", [{"skip": "abc"}, {"limit": "abc"}])
def test_item_list_rejects_non_integer_pagination(base_url, auth_headers, params):
    # skip 和 limit 是数字，传入文字时应由接口参数校验拦截。
    response = requests.get(
        f"{base_url}{API_PREFIX}/items/",
        headers=auth_headers,
        params=params,
        timeout=10,
    )

    assert response.status_code == 422


def test_item_list_skip_past_end_returns_empty_data(base_url, auth_headers):
    # 翻到远超过总记录数的页时，应该返回空数组，而不是报服务器错误。
    response = requests.get(
        f"{base_url}{API_PREFIX}/items/",
        headers=auth_headers,
        params={"skip": 100000, "limit": 10},
        timeout=10,
    )

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_create_item_with_invalid_json_is_rejected(base_url, auth_headers):
    # 请求体不是合法 JSON 时，不能绕过模型校验写入数据库。
    headers = {**auth_headers, "Content-Type": "application/json"}
    response = requests.post(
        f"{base_url}{API_PREFIX}/items/",
        headers=headers,
        data="{invalid-json",
        timeout=10,
    )

    assert response.status_code == 422


def test_update_item_with_invalid_json_is_rejected(base_url, auth_headers, created_item):
    # 修改接口同样必须先通过 JSON 解析，错误内容不能进入业务逻辑。
    headers = {**auth_headers, "Content-Type": "application/json"}
    response = requests.put(
        f"{base_url}{API_PREFIX}/items/{created_item['id']}",
        headers=headers,
        data="{invalid-json",
        timeout=10,
    )

    assert response.status_code == 422


def test_patch_item_method_is_not_allowed(base_url, auth_headers, created_item):
    # 这个接口只设计了 PUT 修改，误用 PATCH 时应明确返回 405。
    response = requests.patch(
        f"{base_url}{API_PREFIX}/items/{created_item['id']}",
        headers=auth_headers,
        json={"title": "不支持的修改方式"},
        timeout=10,
    )

    assert response.status_code == 405


def test_delete_item_twice_returns_not_found(base_url, auth_headers, created_item):
    # 第一次删除成功，第二次删除同一编号应告诉调用方数据不存在。
    item_id = created_item["id"]
    first_response = requests.delete(
        f"{base_url}{API_PREFIX}/items/{item_id}",
        headers=auth_headers,
        timeout=10,
    )
    second_response = requests.delete(
        f"{base_url}{API_PREFIX}/items/{item_id}",
        headers=auth_headers,
        timeout=10,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 404
    assert second_response.json()["detail"] == "Item not found"
