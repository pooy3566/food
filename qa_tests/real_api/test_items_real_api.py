"""真实物品接口的 CRUD 和权限测试。"""

import uuid

import pytest
import requests

from conftest import API_PREFIX


pytestmark = pytest.mark.regression


def test_logged_in_user_can_create_item(base_url, auth_headers, test_user):
    # 像员工拿着工作卡新增货物，创建后应返回完整的物品信息和所属账号。
    payload = {"title": "接口自动化学习笔记", "description": "真实服务测试数据"}
    response = requests.post(
        f"{base_url}{API_PREFIX}/items/",
        headers=auth_headers,
        json=payload,
        timeout=10,
    )

    assert response.status_code == 200
    assert response.json()["title"] == payload["title"]
    assert response.json()["description"] == payload["description"]
    assert response.json()["owner_id"] == test_user["id"]


def test_created_item_can_be_read_and_updated(base_url, auth_headers, created_item):
    # 先查到这条物品，再修改它，检查完整的增查改流程。
    item_id = created_item["id"]
    get_response = requests.get(
        f"{base_url}{API_PREFIX}/items/{item_id}",
        headers=auth_headers,
        timeout=10,
    )
    update_response = requests.put(
        f"{base_url}{API_PREFIX}/items/{item_id}",
        headers=auth_headers,
        json={"title": "修改后的物品", "description": "修改后的说明"},
        timeout=10,
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == item_id
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "修改后的物品"
    assert update_response.json()["description"] == "修改后的说明"


def test_user_can_only_see_own_items(base_url, auth_headers, created_item):
    # 普通账号查看列表时，服务只应返回自己创建的数据。
    response = requests.get(
        f"{base_url}{API_PREFIX}/items/", headers=auth_headers, timeout=10
    )
    result = response.json()

    assert response.status_code == 200
    assert result["count"] >= 1
    assert any(item["id"] == created_item["id"] for item in result["data"])


def test_item_requires_token(base_url):
    # 没有工作卡不能创建物品，防止匿名用户写入数据。
    response = requests.post(
        f"{base_url}{API_PREFIX}/items/",
        json={"title": "不应创建成功"},
        timeout=10,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_missing_item_returns_not_found(base_url, auth_headers):
    # 查询不存在的编号，接口应返回 404，而不是把异常吞掉。
    response = requests.get(
        f"{base_url}{API_PREFIX}/items/{uuid.uuid4()}",
        headers=auth_headers,
        timeout=10,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_item_title_is_validated(base_url, auth_headers):
    # 标题是必填项；空字符串会在进入业务逻辑前被参数校验拦住。
    response = requests.post(
        f"{base_url}{API_PREFIX}/items/",
        headers=auth_headers,
        json={"title": ""},
        timeout=10,
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"][-1] == "title" for error in errors)


def test_user_can_delete_own_item(base_url, auth_headers, created_item):
    # 删除后再查询同一编号，应确认数据已经不存在。
    item_id = created_item["id"]
    delete_response = requests.delete(
        f"{base_url}{API_PREFIX}/items/{item_id}",
        headers=auth_headers,
        timeout=10,
    )
    get_response = requests.get(
        f"{base_url}{API_PREFIX}/items/{item_id}",
        headers=auth_headers,
        timeout=10,
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Item deleted successfully"
    assert get_response.status_code == 404


def test_user_cannot_operate_another_users_item(
    base_url, auth_headers, second_user, created_item
):
    # 账号 A 创建的数据，账号 B 不能查看、修改或删除。
    item_id = created_item["id"]
    other_headers = second_user["headers"]

    get_response = requests.get(
        f"{base_url}{API_PREFIX}/items/{item_id}",
        headers=other_headers,
        timeout=10,
    )
    update_response = requests.put(
        f"{base_url}{API_PREFIX}/items/{item_id}",
        headers=other_headers,
        json={"title": "越权修改"},
        timeout=10,
    )
    delete_response = requests.delete(
        f"{base_url}{API_PREFIX}/items/{item_id}",
        headers=other_headers,
        timeout=10,
    )

    assert get_response.status_code == 403
    assert update_response.status_code == 403
    assert delete_response.status_code == 403
    assert get_response.json()["detail"] == "Not enough permissions"
