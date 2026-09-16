import logging
import pytest
import uuid

import requests


# 这个文件里的物品场景属于完整回归测试
pytestmark = pytest.mark.regression


logger = logging.getLogger("qa_tests.items")


def test_authenticated_user_can_create_item(base_url, auth_headers):
    # 登录用户创建物品，检查返回内容是否和提交的数据一致
    response = requests.post(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        json={"title": "Python 测试笔记", "description": "学习接口自动化"},
        timeout=5,
    )
    # 把响应正文保存下来，方便检查字段是否完整
    result = response.json()

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    assert {"id", "title", "description"} <= result.keys()
    assert result["title"] == "Python 测试笔记"
    assert result["description"] == "学习接口自动化"
    assert result["id"]


def test_create_item_without_token_is_rejected(base_url):
    # 没有 Token 时创建物品，接口应该拒绝请求
    response = requests.post(
        f"{base_url}/api/v1/items/",
        headers={},
        json={"title": "没有权限的物品"},
        timeout=5,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"


def test_list_items_without_token_is_rejected(base_url):
    # 没有 Token 时查询物品列表，也应该拒绝访问
    response = requests.get(
        f"{base_url}/api/v1/items/",
        headers={},
        timeout=5,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"


def test_item_endpoint_allows_cors_preflight(base_url):
    # 浏览器正式发送带 Token 的请求前，会先询问接口是否允许
    response = requests.options(
        f"{base_url}/api/v1/items/",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
        timeout=5,
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert "Authorization" in response.headers["Access-Control-Allow-Headers"]


def test_create_item_without_title_is_rejected(base_url, auth_headers):
    # 缺少标题属于无效请求，应该返回参数校验错误
    response = requests.post(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        json={"description": "缺少标题"},
        timeout=5,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Title is required"


def test_create_item_with_blank_title_is_rejected(base_url, auth_headers):
    # 标题只有空格也视为没有填写标题
    response = requests.post(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        json={"title": "   "},
        timeout=5,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Title is required"


def test_create_item_with_invalid_json_is_rejected(base_url, auth_headers):
    # 请求正文不是合法 JSON 时，接口应该返回格式错误
    response = requests.post(
        f"{base_url}/api/v1/items/",
        headers={**auth_headers, "Content-Type": "application/json"},
        data='{"title":',
        timeout=5,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid JSON"


def test_created_item_can_be_found_in_item_list(base_url, auth_headers, created_item):
    # 先查询物品列表，确认刚创建的数据确实能被找到
    list_response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        timeout=5,
    )
    # 列表接口除了状态码，还要保证返回结构和字段类型正确
    item_list = list_response.json()
    logger.info(
        "GET %s -> status=%s, count=%s, returned=%s",
        list_response.url,
        list_response.status_code,
        item_list["count"],
        len(item_list["data"]),
    )

    assert created_item["title"] == "Fixture 测试物品"
    assert created_item["id"]
    assert list_response.status_code == 200
    assert list_response.headers["Content-Type"].startswith("application/json")
    assert isinstance(item_list["data"], list)
    assert isinstance(item_list["count"], int)
    assert item_list["count"] >= 1
    assert any(item["id"] == created_item["id"] for item in item_list["data"])


def test_authenticated_user_can_get_item_by_id(base_url, auth_headers, created_item):
    # 登录后按物品 ID 查询，应返回正确的那条数据
    response = requests.get(
        f"{base_url}/api/v1/items/{created_item['id']}",
        headers=auth_headers,
        timeout=5,
    )
    result = response.json()

    assert response.status_code == 200
    assert result["id"] == created_item["id"]
    assert result["title"] == "Fixture 测试物品"


def test_get_missing_item_returns_not_found(base_url, auth_headers):
    # 查询不存在的物品 ID 时，接口应该返回 404
    missing_item_id = str(uuid.uuid4())
    response = requests.get(
        f"{base_url}/api/v1/items/{missing_item_id}",
        headers=auth_headers,
        timeout=5,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_get_item_without_token_is_rejected(base_url, created_item):
    # 没有 Token 时不允许查看单条物品详情
    response = requests.get(
        f"{base_url}/api/v1/items/{created_item['id']}",
        headers={},
        timeout=5,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"


def test_item_list_can_be_filtered_by_keyword(base_url, auth_headers, created_item):
    # 搜索标题中的关键词时，返回结果应该包含匹配的物品
    response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        params={"keyword": "Fixture"},
        timeout=5,
    )
    result = response.json()

    assert response.status_code == 200
    assert result["count"] >= 1
    assert any(item["id"] == created_item["id"] for item in result["data"])


def test_item_list_keyword_with_no_match_returns_empty_data(base_url, auth_headers):
    # 搜索没有任何匹配数据的关键词时，应正常返回空列表
    response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        params={"keyword": "definitely-not-a-real-item"},
        timeout=5,
    )

    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}


@pytest.mark.parametrize(
    ("order", "expected_titles"),
    [
        ("asc", ["分页测试物品 1", "分页测试物品 2"]),
        ("desc", ["分页测试物品 2", "分页测试物品 1"]),
    ],
)
def test_item_list_can_be_sorted_by_title(
    base_url, auth_headers, created_items, order, expected_titles
):
    # 搜索固定的两条数据，再检查标题正序和倒序是否正确
    response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        params={"keyword": "分页测试物品", "order": order},
        timeout=5,
    )
    titles = [item["title"] for item in response.json()["data"]]

    assert response.status_code == 200
    assert titles == expected_titles


def test_item_list_rejects_unknown_sort_order(base_url, auth_headers):
    # 排序规则不在接口约定范围内时，应该给出明确提示
    response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        params={"order": "random"},
        timeout=5,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "order must be asc or desc"


def test_item_list_limit_returns_at_most_requested_count(
    base_url, auth_headers, created_item
):
    # limit 用来控制一次最多返回多少条物品
    response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        params={"limit": 1},
        timeout=5,
    )
    result = response.json()

    assert response.status_code == 200
    assert result["count"] >= 1
    assert len(result["data"]) <= 1


def test_item_list_entries_have_expected_data_types(base_url, auth_headers, created_item):
    # 列表里的每条物品都应该包含可用的 ID、标题和说明
    response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        timeout=5,
    )
    item_list = response.json()["data"]

    assert response.status_code == 200
    assert all(isinstance(item["id"], str) and item["id"] for item in item_list)
    assert all(isinstance(item["title"], str) and item["title"] for item in item_list)
    assert all(
        item["description"] is None or isinstance(item["description"], str)
        for item in item_list
    )


def test_item_list_skip_returns_the_next_item(base_url, auth_headers, created_items):
    # 先拿完整列表，再跳过第一条，确认分页结果对应第二条数据
    full_response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        timeout=5,
    )
    page_response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        params={"skip": 1, "limit": 1},
        timeout=5,
    )
    full_result = full_response.json()
    page_result = page_response.json()

    assert full_response.status_code == 200
    assert page_response.status_code == 200
    assert page_result["data"] == full_result["data"][1:2]


def test_item_list_count_does_not_change_after_paging(
    base_url, auth_headers, created_items
):
    # 翻页只改变当前返回的数据，不应该改变物品总数
    full_response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        timeout=5,
    )
    page_response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        params={"skip": 1, "limit": 1},
        timeout=5,
    )

    assert page_response.json()["count"] == full_response.json()["count"]


def test_item_list_skip_beyond_total_returns_empty_data(
    base_url, auth_headers, created_items
):
    # 跳过的数量超过总数时，应该返回空列表，而不是报错
    full_response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        timeout=5,
    )
    total_count = full_response.json()["count"]
    response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        params={"skip": total_count + 10, "limit": 1},
        timeout=5,
    )

    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["count"] == total_count


@pytest.mark.parametrize(
    ("params", "expected_detail"),
    [
        ({"limit": "abc"}, "skip and limit must be integers"),
        ({"skip": -1}, "skip must be >= 0 and limit must be > 0"),
        ({"limit": 0}, "skip must be >= 0 and limit must be > 0"),
    ],
)
def test_item_list_rejects_invalid_pagination(base_url, auth_headers, params, expected_detail):
    # 分页参数格式或范围不正确时，接口应该返回明确的错误提示
    response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        params=params,
        timeout=5,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == expected_detail


def test_authenticated_user_can_update_item(base_url, auth_headers, created_item):
    # 修改刚创建的物品，再检查接口返回的新内容
    item_id = created_item["id"]

    update_response = requests.put(
        f"{base_url}/api/v1/items/{item_id}",
        headers=auth_headers,
        json={"title": "修改后标题", "description": "已更新"},
        timeout=5,
    )
    result = update_response.json()

    assert update_response.status_code == 200
    assert update_response.headers["Content-Type"].startswith("application/json")
    assert {"id", "title", "description"} <= result.keys()
    assert result["id"] == item_id
    assert result["title"] == "修改后标题"
    assert result["description"] == "已更新"


def test_update_item_without_token_is_rejected(base_url, created_item):
    # 没有 Token 时修改物品，接口应该拒绝请求
    response = requests.put(
        f"{base_url}/api/v1/items/{created_item['id']}",
        headers={},
        json={"title": "不应该修改成功"},
        timeout=5,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"


def test_item_endpoint_rejects_unsupported_patch_method(base_url, auth_headers, created_item):
    # 物品接口没有设计 PATCH 修改方式，应该明确返回 405
    response = requests.patch(
        f"{base_url}/api/v1/items/{created_item['id']}",
        headers=auth_headers,
        json={"title": "不支持的修改方式"},
        timeout=5,
    )

    assert response.status_code == 405
    assert response.headers["Content-Type"].startswith("application/json")
    assert response.json()["detail"] == "Method not allowed"


def test_authenticated_user_can_delete_item(base_url, auth_headers, created_item):
    # 删除测试物品后再次查询列表，确认它已经不在结果中
    item_id = created_item["id"]

    delete_response = requests.delete(
        f"{base_url}/api/v1/items/{item_id}",
        headers=auth_headers,
        timeout=5,
    )
    list_response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        timeout=5,
    )
    delete_result = delete_response.json()

    assert delete_response.status_code == 200
    assert delete_response.headers["Content-Type"].startswith("application/json")
    assert delete_result.keys() >= {"message"}
    assert delete_result["message"] == "Item deleted successfully"
    assert item_id not in [item["id"] for item in list_response.json()["data"]]


def test_delete_item_without_token_is_rejected(base_url, created_item):
    # 没有 Token 时删除物品，接口应该拒绝请求
    response = requests.delete(
        f"{base_url}/api/v1/items/{created_item['id']}",
        headers={},
        timeout=5,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"


def test_delete_item_twice_returns_not_found(base_url, auth_headers, created_item):
    # 第一次删除应该成功，第二次删除同一个 ID 时应该提示物品不存在
    item_id = created_item["id"]
    first_response = requests.delete(
        f"{base_url}/api/v1/items/{item_id}",
        headers=auth_headers,
        timeout=5,
    )
    second_response = requests.delete(
        f"{base_url}/api/v1/items/{item_id}",
        headers=auth_headers,
        timeout=5,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 404
    assert second_response.json()["detail"] == "Item not found"


def test_update_missing_item_returns_not_found(base_url, auth_headers):
    # 使用不存在的物品 ID 修改数据，应该返回 404
    missing_item_id = str(uuid.uuid4())

    response = requests.put(
        f"{base_url}/api/v1/items/{missing_item_id}",
        headers=auth_headers,
        json={"title": "不存在的物品"},
        timeout=5,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_delete_missing_item_returns_not_found(base_url, auth_headers):
    # 使用不存在的物品 ID 删除数据，应该返回 404
    missing_item_id = str(uuid.uuid4())

    response = requests.delete(
        f"{base_url}/api/v1/items/{missing_item_id}",
        headers=auth_headers,
        timeout=5,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_update_item_with_invalid_json_is_rejected(base_url, auth_headers, created_item):
    # 修改物品时发送错误 JSON，接口应该返回格式错误而不是直接崩溃
    response = requests.put(
        f"{base_url}/api/v1/items/{created_item['id']}",
        headers={**auth_headers, "Content-Type": "application/json"},
        data='{"title":',
        timeout=5,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid JSON"


def test_update_item_without_title_is_rejected(base_url, auth_headers, created_item):
    # 修改物品时缺少标题，也应该被参数校验拦截
    response = requests.put(
        f"{base_url}/api/v1/items/{created_item['id']}",
        headers=auth_headers,
        json={"description": "只有说明，没有标题"},
        timeout=5,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Title is required"


def test_update_item_with_blank_title_is_rejected(base_url, auth_headers, created_item):
    # 修改时标题只有空格，也应该被当作没有填写标题
    response = requests.put(
        f"{base_url}/api/v1/items/{created_item['id']}",
        headers=auth_headers,
        json={"title": "   "},
        timeout=5,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Title is required"
