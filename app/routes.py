from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Any, Callable

from flask import Flask, current_app, jsonify, redirect, request, send_file, send_from_directory, session

from .database import (
    add_item,
    authenticate_user,
    approve_user,
    create_loan,
    create_registered_user,
    create_repository_document,
    create_repository_folder,
    create_violation_record,
    create_venue_booking,
    delete_loan,
    delete_repository_document,
    delete_repository_folder,
    delete_violation_record,
    delete_user,
    delete_venue_booking,
    get_dashboard,
    get_inventory_snapshot,
    get_item_inventory_trend,
    get_document_library,
    get_repository_document,
    get_user_by_id,
    list_users,
    repository_document_path,
    update_item,
    update_loan,
    update_user,
    update_venue_booking,
)


def json_response(data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK):
    response = jsonify(data)
    response.status_code = status
    return response


def json_error(message: str, status: HTTPStatus):
    return json_response({"error": message}, status)


def handle_api(call: Callable[[], dict[str, Any]], status: HTTPStatus = HTTPStatus.OK):
    try:
        return json_response(call(), status)
    except ValueError as exc:
        return json_error(str(exc), HTTPStatus.BAD_REQUEST)
    except Exception as exc:
        return json_error(f"服务器错误：{exc}", HTTPStatus.INTERNAL_SERVER_ERROR)


def payload() -> dict[str, Any]:
    return request.get_json(silent=True) or {}


def web_dir() -> Path:
    return current_app.config["WEB_DIR"]


def session_user() -> dict[str, Any] | None:
    return get_user_by_id(session.get("user_id"))


def admin_required() -> dict[str, Any] | Any:
    user = session_user()
    if user is None:
        return json_error("请先登录。", HTTPStatus.UNAUTHORIZED)
    if not user.get("is_admin"):
        return json_error("只有管理员可以访问用户管理。", HTTPStatus.FORBIDDEN)
    return user


def register_routes(app: Flask) -> None:
    @app.before_request
    def require_login():
        public_paths = {"/login", "/api/login", "/api/register"}
        if request.path in public_paths:
            return None
        if request.path.startswith("/assets/"):
            return None
        if request.path == "/favicon.ico":
            return None
        if session.get("user_id"):
            return None
        if request.path.startswith("/api/"):
            return json_error("请先登录。", HTTPStatus.UNAUTHORIZED)
        return redirect("/login")

    @app.get("/login")
    def login_page():
        if session.get("user_id"):
            return redirect("/")
        return send_from_directory(web_dir(), "login.html")

    @app.post("/api/login")
    def login():
        login_payload = payload()
        try:
            user = authenticate_user(login_payload.get("username"), login_payload.get("password"))
        except ValueError as exc:
            return json_error(str(exc), HTTPStatus.UNAUTHORIZED)
        session.clear()
        session["user_id"] = user["id"]
        return json_response({"user": user})

    @app.post("/api/register")
    def register():
        try:
            user = create_registered_user(payload())
        except ValueError as exc:
            return json_error(str(exc), HTTPStatus.BAD_REQUEST)
        return json_response({"user": user, "pending": True}, HTTPStatus.CREATED)

    @app.post("/api/logout")
    def logout():
        session.clear()
        return json_response({"logged_out": True})

    @app.get("/api/me")
    def me():
        user = session_user()
        if user is None:
            session.clear()
            return json_error("请先登录。", HTTPStatus.UNAUTHORIZED)
        return json_response({"user": user})

    @app.get("/api/users")
    def users():
        admin = admin_required()
        if not isinstance(admin, dict):
            return admin
        return handle_api(list_users)

    @app.put("/api/users/<int:user_id>")
    def edit_user(user_id: int):
        admin = admin_required()
        if not isinstance(admin, dict):
            return admin
        return handle_api(lambda: update_user(user_id, payload()))

    @app.post("/api/users/<int:user_id>/approve")
    def approve_pending_user(user_id: int):
        admin = admin_required()
        if not isinstance(admin, dict):
            return admin
        return handle_api(lambda: approve_user(user_id))

    @app.delete("/api/users/<int:user_id>")
    def remove_user(user_id: int):
        admin = admin_required()
        if not isinstance(admin, dict):
            return admin
        return handle_api(lambda: delete_user(user_id))

    @app.get("/")
    def index():
        return send_from_directory(web_dir(), "index.html")

    @app.get("/api/dashboard")
    def dashboard():
        return handle_api(get_dashboard)

    @app.get("/api/inventory-snapshot")
    def inventory_snapshot():
        snapshot_date = request.args.get("date", "")
        return handle_api(lambda: get_inventory_snapshot(snapshot_date))

    @app.get("/api/item-trend")
    def item_trend():
        item_id = request.args.get("item_id", "0")
        start_date = request.args.get("start_date", "")
        return handle_api(lambda: get_item_inventory_trend(int(item_id), start_date, 10))

    @app.get("/api/repository")
    def repository():
        folder_id = request.args.get("folder_id", "")
        return handle_api(lambda: get_document_library(folder_id))

    @app.post("/api/items")
    def create_item():
        return handle_api(lambda: add_item(payload()), HTTPStatus.CREATED)

    @app.put("/api/items/<int:item_id>")
    def edit_item(item_id: int):
        return handle_api(lambda: update_item(item_id, payload()))

    @app.post("/api/loans")
    def create_material_loan():
        return handle_api(lambda: create_loan(payload()), HTTPStatus.CREATED)

    @app.put("/api/loans/<int:loan_id>")
    def edit_material_loan(loan_id: int):
        return handle_api(lambda: update_loan(loan_id, payload()))

    @app.delete("/api/loans/<int:loan_id>")
    def remove_material_loan(loan_id: int):
        return handle_api(lambda: delete_loan(loan_id))

    @app.post("/api/venue-bookings")
    def create_booking():
        return handle_api(lambda: create_venue_booking(payload()), HTTPStatus.CREATED)

    @app.post("/api/violation-records")
    def create_violation():
        return handle_api(lambda: create_violation_record(payload()), HTTPStatus.CREATED)

    @app.delete("/api/violation-records/<int:record_id>")
    def remove_violation(record_id: int):
        return handle_api(lambda: delete_violation_record(record_id))

    @app.post("/api/repository-folders")
    def create_folder():
        return handle_api(lambda: create_repository_folder(payload()), HTTPStatus.CREATED)

    @app.delete("/api/repository-folders/<int:folder_id>")
    def remove_folder(folder_id: int):
        return handle_api(lambda: delete_repository_folder(folder_id))

    @app.post("/api/repository-documents")
    def upload_document():
        folder_id_raw = request.form.get("folder_id") or "0"
        uploaded_file = request.files.get("file")
        return handle_api(lambda: create_repository_document(int(folder_id_raw), uploaded_file), HTTPStatus.CREATED)

    @app.delete("/api/repository-documents/<int:document_id>")
    def remove_document(document_id: int):
        return handle_api(lambda: delete_repository_document(document_id))

    @app.get("/api/repository-documents/<int:document_id>/file")
    def repository_file(document_id: int):
        try:
            document = get_repository_document(document_id)
            file_path = repository_document_path(document)
            return send_file(
                file_path,
                mimetype=document.get("mime_type") or None,
                as_attachment=request.args.get("download") == "1",
                download_name=document["original_name"],
            )
        except ValueError as exc:
            return json_error(str(exc), HTTPStatus.BAD_REQUEST)

    @app.put("/api/venue-bookings/<int:booking_id>")
    def edit_booking(booking_id: int):
        return handle_api(lambda: update_venue_booking(booking_id, payload()))

    @app.delete("/api/venue-bookings/<int:booking_id>")
    def remove_booking(booking_id: int):
        return handle_api(lambda: delete_venue_booking(booking_id))

    @app.get("/<path:filename>")
    def static_file(filename: str):
        return send_from_directory(web_dir(), filename)
