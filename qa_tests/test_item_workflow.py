import pytest
import requests


# 这个文件检查完整业务流程，属于回归测试
pytestmark = pytest.mark.regression


def test_user_can_complete_item_management_flow(base_url, auth_headers):
    # 按真实使用顺序检查：创建、查询、修改、删除
    item_id = None
    try:
        create_response = requests.post(
            f"{base_url}/api/v1/items/",
            headers=auth_headers,
            json={"title": "流程测试物品", "description": "创建后的说明"},
            timeout=5,
        )
        created_item = create_response.json()
        item_id = created_item["id"]

        assert create_response.status_code == 200
        assert created_item["title"] == "流程测试物品"

        # 创建完成后，列表中应该能查到这条物品
        list_response = requests.get(
            f"{base_url}/api/v1/items/",
            headers=auth_headers,
            timeout=5,
        )
        assert list_response.status_code == 200
        assert any(item["id"] == item_id for item in list_response.json()["data"])

        # 修改后，接口应返回更新过的标题和说明
        update_response = requests.put(
            f"{base_url}/api/v1/items/{item_id}",
            headers=auth_headers,
            json={"title": "流程测试物品已修改", "description": "修改后的说明"},
            timeout=5,
        )
        updated_item = update_response.json()

        assert update_response.status_code == 200
        assert updated_item["title"] == "流程测试物品已修改"
        assert updated_item["description"] == "修改后的说明"

        # 删除成功后，再查询列表时不应再看到该物品
        delete_response = requests.delete(
            f"{base_url}/api/v1/items/{item_id}",
            headers=auth_headers,
            timeout=5,
        )
        final_list_response = requests.get(
            f"{base_url}/api/v1/items/",
            headers=auth_headers,
            timeout=5,
        )

        assert delete_response.status_code == 200
        assert item_id not in [item["id"] for item in final_list_response.json()["data"]]
    finally:
        # 测试中途失败时也尝试删除物品，避免留下测试数据
        if item_id:
            requests.delete(
                f"{base_url}/api/v1/items/{item_id}",
                headers=auth_headers,
                timeout=5,
            )


def test_rejected_item_creation_does_not_add_data(base_url, auth_headers):
    # 创建失败后，物品总数不应该悄悄增加
    before_response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        timeout=5,
    )
    before_count = before_response.json()["count"]

    rejected_response = requests.post(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        json={"title": "   "},
        timeout=5,
    )
    after_response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        timeout=5,
    )

    assert rejected_response.status_code == 422
    assert after_response.json()["count"] == before_count


def test_rejected_item_update_keeps_original_data(base_url, auth_headers, created_item):
    # 修改被拒绝后，原来的标题和说明都应该保持不变
    original_title = created_item["title"]
    original_description = created_item["description"]

    rejected_response = requests.put(
        f"{base_url}/api/v1/items/{created_item['id']}",
        headers=auth_headers,
        json={"title": "   ", "description": "不应该保存"},
        timeout=5,
    )
    list_response = requests.get(
        f"{base_url}/api/v1/items/",
        headers=auth_headers,
        timeout=5,
    )
    current_item = next(
        item for item in list_response.json()["data"] if item["id"] == created_item["id"]
    )

    assert rejected_response.status_code == 422
    assert current_item["title"] == original_title
    assert current_item["description"] == original_description
