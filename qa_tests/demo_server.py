import csv
import json
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO
from urllib.parse import parse_qs, urlparse


registered_emails = {"admin@example.com"}
items = []
ALLOWED_ORIGIN = "http://localhost:5173"


class DemoHandler(BaseHTTPRequestHandler):
    def _send_request_id(self):
        # 调用方传了编号就原样返回，否则由服务生成一个新的追踪编号
        request_id = self.headers.get("X-Request-ID") or str(uuid.uuid4())
        self.send_header("X-Request-ID", request_id)

    def _send_cors_headers(self):
        # 只允许本地前端开发服务访问接口
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)

    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_request_id()
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_csv(self, filename, rows):
        # 使用内存中的文本缓冲区生成 CSV，避免在服务端留下临时文件
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["id", "title", "description"],
        )
        writer.writeheader()
        writer.writerows(rows)
        body = output.getvalue().encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{filename}"',
        )
        self.send_header("Content-Length", str(len(body)))
        self._send_request_id()
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        # 浏览器预检请求时，告诉它允许使用哪些请求方法和请求头
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self._send_request_id()
        self._send_cors_headers()
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, DELETE, OPTIONS",
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization, Content-Type",
        )
        self.end_headers()

    def do_GET(self):
        # 把地址和查询参数分开，支持 /items/?skip=0&limit=10 这样的请求
        parsed_url = urlparse(self.path)
        if parsed_url.path == "/api/v1/items/export":
            if self.headers.get("Authorization", "") != "Bearer demo-token":
                self._send_json(403, {"detail": "Could not validate credentials"})
                return

            # 导出全部物品；浏览器收到附件响应头后会将它作为文件下载
            self._send_csv("items.csv", items)
            return

        if parsed_url.path == "/api/v1/items/":
            if self.headers.get("Authorization", "") != "Bearer demo-token":
                self._send_json(403, {"detail": "Could not validate credentials"})
                return

            # 没有传参数时使用默认值：从第一条开始，最多返回 100 条
            query = parse_qs(parsed_url.query)
            try:
                skip = int(query.get("skip", [0])[0])
                limit = int(query.get("limit", [100])[0])
            except (TypeError, ValueError):
                # 参数必须是整数，传入字母等内容时直接返回提示
                self._send_json(422, {"detail": "skip and limit must be integers"})
                return

            # skip 不能为负数，limit 至少要返回一条数据
            if skip < 0 or limit <= 0:
                self._send_json(
                    422,
                    {"detail": "skip must be >= 0 and limit must be > 0"},
                )
                return

            keyword = query.get("keyword", [""])[0].strip().lower()
            # 有搜索词时，只保留标题或说明中包含该词的物品
            filtered_items = items
            if keyword:
                filtered_items = [
                    item
                    for item in items
                    if keyword in item["title"].lower()
                    or keyword in (item["description"] or "").lower()
                ]

            order = query.get("order", ["asc"])[0].lower()
            if order not in ("asc", "desc"):
                self._send_json(422, {"detail": "order must be asc or desc"})
                return

            # 按标题排序；reverse 为 True 时表示从 Z 到 A 的倒序
            sorted_items = sorted(
                filtered_items,
                key=lambda item: item["title"].lower(),
                reverse=order == "desc",
            )
            page_items = sorted_items[skip : skip + limit]
            self._send_json(200, {"data": page_items, "count": len(filtered_items)})
            return

        if parsed_url.path.startswith("/api/v1/items/"):
            if self.headers.get("Authorization", "") != "Bearer demo-token":
                self._send_json(403, {"detail": "Could not validate credentials"})
                return

            # 根据 URL 中的物品 ID 查找单条数据
            item_id = parsed_url.path.rsplit("/", 1)[-1]
            item = next((item for item in items if item["id"] == item_id), None)
            if item is None:
                self._send_json(404, {"detail": "Item not found"})
                return

            self._send_json(200, item)
            return

        if parsed_url.path != "/api/v1/utils/health-check/":
            # 未知地址也使用统一的 JSON 错误格式，方便调用方处理
            self._send_json(404, {"detail": "Not found"})
            return

        # 健康检查也走统一响应方法，保证 JSON 和 CORS 请求头一致
        self._send_json(200, True)

    def do_POST(self):
        if self.path == "/api/v1/items/":
            if self.headers.get("Authorization", "") != "Bearer demo-token":
                self._send_json(403, {"detail": "Could not validate credentials"})
                return

            length = int(self.headers.get("Content-Length", 0))
            try:
                item_data = json.loads(self.rfile.read(length).decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json(422, {"detail": "Invalid JSON"})
                return

            title = item_data.get("title", "")
            if not title.strip():
                self._send_json(422, {"detail": "Title is required"})
                return

            item = {
                "id": str(uuid.uuid4()),
                "title": title,
                "description": item_data.get("description"),
            }
            items.append(item)
            self._send_json(200, item)
            return

        if self.path == "/api/v1/users/signup":
            length = int(self.headers.get("Content-Length", 0))
            try:
                user_data = json.loads(self.rfile.read(length).decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json(422, {"detail": "Invalid JSON"})
                return

            email = user_data.get("email", "")
            password = user_data.get("password", "")
            if len(password) < 8:
                self._send_json(422, {"detail": "Password should have at least 8 characters"})
            elif "@" not in email or "." not in email.split("@")[-1]:
                self._send_json(422, {"detail": "Invalid email format"})
            elif email in registered_emails:
                self._send_json(
                    400,
                    {"detail": "The user with this email already exists in the system"},
                )
            else:
                registered_emails.add(email)
                self._send_json(
                    200,
                    {
                        "email": email,
                        "full_name": user_data.get("full_name"),
                        "is_active": True,
                    },
                )
            return

        if self.path == "/api/v1/login/test-token":
            authorization = self.headers.get("Authorization", "")
            if authorization == "Bearer demo-token":
                self._send_json(
                    200,
                    {"email": "admin@example.com", "is_active": True},
                )
            else:
                self._send_json(403, {"detail": "Could not validate credentials"})
            return

        if self.path != "/api/v1/login/access-token":
            self._send_json(404, {"detail": "Not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        form_data = parse_qs(self.rfile.read(length).decode("utf-8"))
        username = form_data.get("username", [""])[0]
        password = form_data.get("password", [""])[0]

        if username == "admin@example.com" and password == "changethis":
            self._send_json(200, {"access_token": "demo-token", "token_type": "bearer"})
        else:
            self._send_json(400, {"detail": "Incorrect email or password"})

    def do_PUT(self):
        if not self.path.startswith("/api/v1/items/"):
            self._send_json(404, {"detail": "Not found"})
            return
        if self.headers.get("Authorization", "") != "Bearer demo-token":
            self._send_json(403, {"detail": "Could not validate credentials"})
            return

        item_id = self.path.rsplit("/", 1)[-1]
        item = next((item for item in items if item["id"] == item_id), None)
        if item is None:
            self._send_json(404, {"detail": "Item not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        # 修改接口也要先检查请求正文，避免错误 JSON 让服务抛出异常
        try:
            item_data = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(422, {"detail": "Invalid JSON"})
            return

        # 标题为空或只有空格时，不允许覆盖原来的有效标题
        title = item_data.get("title", "")
        if not title.strip():
            self._send_json(422, {"detail": "Title is required"})
            return

        item["title"] = item_data.get("title", item["title"])
        item["description"] = item_data.get("description", item["description"])
        self._send_json(200, item)

    def do_PATCH(self):
        # 当前演示接口只支持 PUT 修改，收到 PATCH 时返回统一错误格式
        self._send_json(405, {"detail": "Method not allowed"})

    def do_DELETE(self):
        if not self.path.startswith("/api/v1/items/"):
            self._send_json(404, {"detail": "Not found"})
            return
        if self.headers.get("Authorization", "") != "Bearer demo-token":
            self._send_json(403, {"detail": "Could not validate credentials"})
            return

        item_id = self.path.rsplit("/", 1)[-1]
        item = next((item for item in items if item["id"] == item_id), None)
        if item is None:
            self._send_json(404, {"detail": "Item not found"})
            return

        items.remove(item)
        self._send_json(200, {"message": "Item deleted successfully"})

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = HTTPServer(("localhost", 8000), DemoHandler)
    print("Demo API is running at http://localhost:8000")
    server.serve_forever()
