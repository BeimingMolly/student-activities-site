from __future__ import annotations

from app import create_app


HOST = "127.0.0.1"
PORT = 8000

app = create_app()


def main() -> None:
    print(f"学活物资与场地借用管理系统已启动：http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
