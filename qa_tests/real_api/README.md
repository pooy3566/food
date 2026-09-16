# 真实 FastAPI 接口测试

这套测试直接调用项目中的 FastAPI 后端，不依赖练习用的 `demo_server.py`。
测试使用 Python、pytest 和 requests，模拟真实客户端发送 HTTP 请求。

## 测试范围

- `test_smoke_real_api.py`：健康检查、注册登录、Token 访问，快速确认服务能用。
- `test_login_real_api.py`：错误密码、未知账号、停用账号、缺少登录字段和敏感信息泄露。
- `test_register_real_api.py`：重复邮箱、邮箱格式、密码长度和注册返回值。
- `test_items_real_api.py`：物品新增、查询、修改、删除和用户之间的越权访问。
- `test_items_boundary_real_api.py`：分页、非法 JSON、错误分页参数、错误 HTTP 方法和重复删除。
- `test_users_real_api.py`：修改个人资料、修改密码和密码错误场景。
- `test_admin_users_real_api.py`：管理员查看、创建、修改、删除用户，以及普通用户权限边界。
- `test_token_boundary_real_api.py`：伪造 Token 和匿名访问受保护接口。
- `test_service_contract_real_api.py`：未知地址、OpenAPI 路由目录和本地跨域预检。

## 运行方式

先确保 PostgreSQL 和 FastAPI 服务已经启动，然后运行：

```powershell
cd D:\Personal\Documents\ChatGPT\11\qa-fastapi-project\qa_tests
D:\DevData\venvs\qa-fastapi\Scripts\python.exe -m pytest real_api -v
```

默认接口地址为 `http://localhost:8000`，可以通过 `BASE_URL` 切换测试环境：

```powershell
$env:BASE_URL = "http://localhost:8001"
```

## 测试数据清理

测试会自动创建临时账号和物品。普通测试结束后由 fixture 删除；管理员测试会在创建、修改后删除临时用户，避免污染数据库。

## 测试分类

只跑关键冒烟测试：

```powershell
pytest real_api -m smoke -v
```

运行完整回归测试：

```powershell
pytest real_api -m regression -v
```

生成 HTML 报告：

```powershell
pytest real_api -v --html=reports/real-api-report.html --self-contained-html
```

## 最近一次结果

```text
49 passed
```
