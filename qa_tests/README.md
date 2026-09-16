# QA Tests

## 真实 FastAPI 项目测试

项目的主要接口自动化测试位于 `real_api/`，直接调用 `backend/` 中的 FastAPI 服务，覆盖登录、注册、Token、物品、用户资料和管理员权限。

服务启动后，在 `qa_tests` 目录运行：

```powershell
D:\DevData\venvs\qa-fastapi\Scripts\python.exe -m pytest real_api -v
```

最近一次真实接口回归结果：`49 passed`。

详细测试范围和清理规则见 [`real_api/README.md`](real_api/README.md)。

These tests call the running FastAPI application from outside the backend code.

## Install

```powershell
py -m pip install -r requirements.txt
```

## Start the demo API

Open a second PowerShell window, enter the `qa_tests` directory, and run:

```powershell
py demo_server.py
```

Keep that window running.

## Run tests

The demo application runs at `http://localhost:8000`.

```powershell
py -m pytest -v
```

## 一键运行全部测试

如果不想手动打开两个终端，可以在项目根目录运行：

```powershell
py qa_tests\run_tests.py
```

脚本会自动启动演示服务、运行全部测试、生成报告；如果服务原本没有启动，测试结束后会自动关闭它。

## 按类型运行测试

冒烟测试只检查最关键的几条链路，适合快速确认服务是否基本正常：

```powershell
py -m pytest -v -m smoke
```

回归测试会检查已有接口功能，适合代码修改后做完整验证：

```powershell
py -m pytest -v -m regression
```

## Generate a test report

Create a machine-readable JUnit XML report for CI systems:

```powershell
New-Item -ItemType Directory -Force reports
py -m pytest -v --junitxml=reports\junit.xml
```

The report is written to `reports\junit.xml`. It records the test names, status, and duration.

## Generate an HTML report

Use the following command to generate a report that is easier to read in a browser:

```powershell
New-Item -ItemType Directory -Force reports
py -m pytest -v --html=reports\report.html --self-contained-html
```

The report is written to `reports\report.html`. Open that file in a browser to see the test results, duration, and failure details.

测试运行时还会把每条测试的结果、耗时和关键请求记录到 `reports\test.log`，出现问题时可以先查看日志定位问题。

To test another environment:

```powershell
$env:BASE_URL = "http://localhost:8001"
py -m pytest -v
```

## 配置测试账号

公共登录 fixture 默认使用演示服务账号。如果测试真实环境，可以在当前 PowerShell 窗口设置账号信息：

```powershell
$env:TEST_USERNAME = "your-test-account@example.com"
$env:TEST_PASSWORD = "your-test-password"
py -m pytest -v
```

账号密码只保存在当前终端的环境变量中，不要把真实密码写进测试代码或提交到 GitHub。

## 请求编号

每个接口响应都会带 `X-Request-ID`。调用方可以主动传入该请求头，服务会原样返回；没有传入时，服务会自动生成一个编号，方便根据编号查找对应日志。

## 前端跨域访问

演示服务允许本地前端开发地址 `http://localhost:5173` 访问接口，并支持浏览器在正式请求前发送的 `OPTIONS` 预检请求。

这类规则会在 `test_health.py` 和 `test_items.py` 中自动检查。

## 查询物品列表：分页和搜索

物品列表接口支持两个查询参数：

```text
skip：跳过前面多少条数据，默认是 0
limit：最多返回多少条数据，默认是 100
```

例如下面的地址表示跳过前 10 条，最多返回 5 条：

```text
/api/v1/items/?skip=10&limit=5
```

列表还支持 `keyword` 搜索参数，会在物品标题和说明中查找关键词。例如：

```text
/api/v1/items/?keyword=Python
```

搜索时，`count` 表示搜索到的物品总数；`data` 再根据 `skip` 和 `limit` 返回当前页的数据。

还可以通过 `order` 按标题排序：`asc` 表示从 A 到 Z，`desc` 表示从 Z 到 A。默认是 `asc`：

```text
/api/v1/items/?keyword=Python&order=desc
```

## 导出物品清单

登录用户可以访问下面的接口，下载 CSV 格式的物品清单。CSV 可以直接用 Excel 打开：

```text
GET /api/v1/items/export
```

接口会返回 `Content-Disposition: attachment` 响应头，浏览器据此把响应当作下载文件，而不是普通网页内容。导出接口也需要 Token，并且同样带有 `X-Request-ID` 请求编号。

## GitHub Actions 自动测试

仓库中的 `.github/workflows/qa-tests.yml` 会在 push 或 pull request 时自动运行这套接口测试。

查看方式：打开 GitHub 仓库的 **Actions** 页面，选择 **QA API Tests** 工作流；运行结束后，在页面底部的 **Artifacts** 区域下载测试报告。
