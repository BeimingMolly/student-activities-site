from __future__ import annotations

from datetime import date, datetime, timedelta
import mimetypes
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "app.sqlite3"
VENUE_TIME_SLOTS = {
    ("08:00", "12:00"),
    ("14:00", "17:00"),
    ("19:00", "22:00"),
}
MATERIAL_TIME_SLOTS = {"12:40", "17:30", "21:00"}
CURRENT_ACTIVE_LOAN_CONDITION = """
loans.status = 'Borrowed'
AND datetime(loans.loan_date || ' ' || loans.loan_time) <= datetime('now', 'localtime')
AND datetime(loans.due_date || ' ' || loans.due_time) > datetime('now', 'localtime')
""".strip()
SNAPSHOT_ACTIVE_LOAN_CONDITION = """
loans.status = 'Borrowed'
AND datetime(loans.loan_date || ' ' || loans.loan_time) <= datetime(? || ' 23:59')
AND datetime(loans.due_date || ' ' || loans.due_time) > datetime(? || ' 00:00')
""".strip()
SNAPSHOT_CURRENT_LOAN_CONDITION = """
loans.status = 'Borrowed'
AND datetime(loans.loan_date || ' ' || loans.loan_time) <= datetime('now', 'localtime')
AND datetime(loans.due_date || ' ' || loans.due_time) > datetime('now', 'localtime')
""".strip()
DEFAULT_ITEMS = [
    {"name": "塑料椅", "category": "桌椅类", "total_quantity": 80, "unit": "把", "location": "物资间", "size": "无", "note": ""},
    {"name": "折叠桌", "category": "桌椅类", "total_quantity": 12, "unit": "张", "location": "物资间", "size": "无", "note": ""},
    {"name": "帐篷", "category": "布置类", "total_quantity": 6, "unit": "顶", "location": "物资间", "size": "无", "note": ""},
    {"name": "海报板", "category": "宣传类", "total_quantity": 20, "unit": "块", "location": "物资间", "size": "无", "note": ""},
    {"name": "拉杆音响", "category": "设备类", "total_quantity": 2, "unit": "台", "location": "办公室", "size": "无", "note": ""},
    {"name": "小蜜蜂", "category": "设备类", "total_quantity": 6, "unit": "个", "location": "办公室", "size": "无", "note": ""},
    {"name": "扩音器", "category": "设备类", "total_quantity": 4, "unit": "个", "location": "办公室", "size": "无", "note": ""},
    {"name": "桌布", "category": "布置类", "total_quantity": 12, "unit": "张", "location": "物资间", "size": "无", "note": ""},
]
MAX_UPLOAD_SIZE = 25 * 1024 * 1024
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+")
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
}
REPOSITORY_ROOT_NAME = "数据仓库"
DEFAULT_LOGIN_USERNAME = "admin"
DEFAULT_LOGIN_PASSWORD = "admin123"


def uploads_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def parse_date(value: str, field_name: str) -> date:
    date_value = str(value or "").strip()
    if not date_value:
        raise ValueError(f"请选择{field_name}。")
    try:
        return date.fromisoformat(date_value)
    except ValueError as exc:
        raise ValueError(f"{field_name}格式不正确。") from exc


def validate_phone(value: Any) -> str:
    phone = str(value or "").strip()
    if len(phone) != 11 or not phone.isdigit():
        raise ValueError("手机号必须是 11 位数字。")
    return phone


def validate_student_id(value: Any) -> str:
    student_id = str(value or "").strip()
    if len(student_id) != 10 or not student_id.isdigit():
        raise ValueError("学号必须是 10 位数字。")
    return student_id


def validate_material_time(value: Any, field_name: str) -> str:
    time_value = str(value or "").strip()
    if time_value not in MATERIAL_TIME_SLOTS:
        raise ValueError(f"{field_name}只能选择 12:40、17:30、21:00。")
    return time_value


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '通用',
                total_quantity INTEGER NOT NULL CHECK (total_quantity >= 0),
                unit TEXT NOT NULL DEFAULT '件',
                location TEXT NOT NULL DEFAULT '',
                size TEXT NOT NULL DEFAULT '无',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS venues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                capacity INTEGER NOT NULL DEFAULT 0 CHECK (capacity >= 0),
                location TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Available',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                borrower TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT '',
                contact TEXT NOT NULL DEFAULT '',
                purpose TEXT NOT NULL DEFAULT '',
                loan_date TEXT NOT NULL,
                loan_time TEXT NOT NULL DEFAULT '12:40',
                due_date TEXT NOT NULL,
                due_time TEXT NOT NULL DEFAULT '12:40',
                return_date TEXT,
                status TEXT NOT NULL DEFAULT 'Borrowed',
                custom_item_name TEXT NOT NULL DEFAULT '',
                custom_item_quantity INTEGER NOT NULL DEFAULT 0 CHECK (custom_item_quantity >= 0),
                custom_item_unit TEXT NOT NULL DEFAULT '件',
                source_venue_booking_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS loan_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
                item_id INTEGER NOT NULL REFERENCES items(id),
                quantity INTEGER NOT NULL CHECK (quantity > 0)
            );

            CREATE TABLE IF NOT EXISTS loan_venues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
                venue_id INTEGER NOT NULL REFERENCES venues(id)
            );

            CREATE TABLE IF NOT EXISTS venue_bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                borrower TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT '',
                contact TEXT NOT NULL DEFAULT '',
                purpose TEXT NOT NULL DEFAULT '',
                setup_time TEXT NOT NULL DEFAULT '',
                estimated_attendance INTEGER NOT NULL DEFAULT 0 CHECK (estimated_attendance >= 0),
                booking_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Booked',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS violation_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                borrower TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT '',
                contact TEXT NOT NULL DEFAULT '',
                damaged_item TEXT NOT NULL DEFAULT '',
                resolution TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS repository_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER REFERENCES repository_folders(id) ON DELETE RESTRICT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS repository_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id INTEGER NOT NULL REFERENCES repository_folders(id) ON DELETE RESTRICT,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL UNIQUE,
                mime_type TEXT NOT NULL DEFAULT '',
                file_size INTEGER NOT NULL DEFAULT 0 CHECK (file_size >= 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                student_id TEXT UNIQUE,
                phone TEXT NOT NULL DEFAULT '',
                approval_status TEXT NOT NULL DEFAULT 'approved',
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        ensure_item_schema(conn)
        ensure_loan_schema(conn)
        ensure_venue_booking_schema(conn)
        ensure_user_schema(conn)
        venue_count = conn.execute("SELECT COUNT(*) FROM venues").fetchone()[0]

        sync_default_items(conn)
        ensure_repository_root(conn)
        ensure_default_user(conn)

        if venue_count == 0:
            conn.executemany(
                """
                INSERT INTO venues (name, capacity, location, status, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    ("学生活动室 101", 60, "一楼", "Available", "含投影设备"),
                    ("多功能厅", 220, "二楼", "Available", "需提前审批"),
                    ("会议室 B", 24, "办公区", "Available", ""),
                ],
            )

        update_sample_data(conn)


def ensure_item_schema(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(items)").fetchall()}
    if "size" not in columns:
        conn.execute("ALTER TABLE items ADD COLUMN size TEXT NOT NULL DEFAULT '无'")


def ensure_loan_schema(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(loans)").fetchall()}
    if "custom_item_name" not in columns:
        conn.execute("ALTER TABLE loans ADD COLUMN custom_item_name TEXT NOT NULL DEFAULT ''")
    if "custom_item_quantity" not in columns:
        conn.execute("ALTER TABLE loans ADD COLUMN custom_item_quantity INTEGER NOT NULL DEFAULT 0")
    if "custom_item_unit" not in columns:
        conn.execute("ALTER TABLE loans ADD COLUMN custom_item_unit TEXT NOT NULL DEFAULT '件'")
    if "loan_time" not in columns:
        conn.execute("ALTER TABLE loans ADD COLUMN loan_time TEXT NOT NULL DEFAULT '12:40'")
    if "due_time" not in columns:
        conn.execute("ALTER TABLE loans ADD COLUMN due_time TEXT NOT NULL DEFAULT '12:40'")
    if "source_venue_booking_id" not in columns:
        conn.execute("ALTER TABLE loans ADD COLUMN source_venue_booking_id INTEGER")


def ensure_venue_booking_schema(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(venue_bookings)").fetchall()}
    if "setup_time" not in columns:
        conn.execute("ALTER TABLE venue_bookings ADD COLUMN setup_time TEXT NOT NULL DEFAULT ''")
    if "estimated_attendance" not in columns:
        conn.execute("ALTER TABLE venue_bookings ADD COLUMN estimated_attendance INTEGER NOT NULL DEFAULT 0")


def ensure_user_schema(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "student_id" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN student_id TEXT")
    if "phone" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT ''")
    if "approval_status" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'approved'")


def ensure_repository_folder_schema(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(repository_folders)").fetchall()}
    if "parent_id" not in columns:
        conn.execute("ALTER TABLE repository_folders ADD COLUMN parent_id INTEGER REFERENCES repository_folders(id) ON DELETE RESTRICT")


def ensure_repository_root(conn: sqlite3.Connection) -> int:
    ensure_repository_folder_schema(conn)
    root = conn.execute(
        """
        SELECT *
        FROM repository_folders
        WHERE name = ?
        ORDER BY parent_id IS NULL DESC, id ASC
        LIMIT 1
        """,
        (REPOSITORY_ROOT_NAME,),
    ).fetchone()

    if root is None:
        cursor = conn.execute(
            "INSERT INTO repository_folders (name, parent_id) VALUES (?, NULL)",
            (REPOSITORY_ROOT_NAME,),
        )
        root_id = cursor.lastrowid
    else:
        root_id = int(root["id"])
        if root["parent_id"] is not None:
            conn.execute("UPDATE repository_folders SET parent_id = NULL WHERE id = ?", (root_id,))

    conn.execute(
        """
        UPDATE repository_folders
        SET parent_id = ?
        WHERE parent_id IS NULL
          AND id <> ?
        """,
        (root_id, root_id),
    )
    return root_id


def ensure_default_user(conn: sqlite3.Connection) -> None:
    admin = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (DEFAULT_LOGIN_USERNAME,),
    ).fetchone()
    if admin:
        conn.execute(
            """
            UPDATE users
            SET password_hash = ?,
                display_name = ?,
                phone = COALESCE(phone, ''),
                approval_status = ?
            WHERE id = ?
            """,
            (
                generate_password_hash(DEFAULT_LOGIN_PASSWORD),
                "管理员",
                "approved",
                admin["id"],
            ),
        )
        return

    conn.execute(
        """
        INSERT INTO users (username, student_id, phone, approval_status, password_hash, display_name)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            DEFAULT_LOGIN_USERNAME,
            None,
            "",
            "approved",
            generate_password_hash(DEFAULT_LOGIN_PASSWORD),
            "管理员",
        ),
    )


def sync_default_items(conn: sqlite3.Connection) -> None:
    for item in DEFAULT_ITEMS:
        existing = conn.execute(
            "SELECT id FROM items WHERE name = ?",
            (item["name"],),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE items
                SET category = ?,
                    unit = ?,
                    location = ?,
                    note = ?,
                    size = CASE
                        WHEN size IS NULL OR TRIM(size) = '' THEN '无'
                        ELSE size
                    END
                WHERE id = ?
                """,
                (
                    item["category"],
                    item["unit"],
                    item["location"],
                    item["note"],
                    existing["id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO items (name, category, total_quantity, unit, location, size, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["name"],
                    item["category"],
                    item["total_quantity"],
                    item["unit"],
                    item["location"],
                    item["size"],
                    item["note"],
                ),
            )

    conn.execute(
        """
        DELETE FROM items
        WHERE name = '插线板'
          AND NOT EXISTS (
              SELECT 1
              FROM loan_items
              WHERE loan_items.item_id = items.id
          )
        """
    )


def update_sample_data(conn: sqlite3.Connection) -> None:
    item_updates = [
        ("折叠桌", "桌椅类", "张", "物资间", "", "Folding Table"),
        ("塑料椅", "桌椅类", "把", "物资间", "", "Plastic Chair"),
        ("扩音器", "设备类", "个", "办公室", "", "Megaphone"),
    ]
    conn.executemany(
        """
        UPDATE items
        SET name = ?, category = ?, unit = ?, location = ?, note = ?
        WHERE name = ?
        """,
        item_updates,
    )

    venue_updates = [
        ("学生活动室 101", "一楼", "含投影设备", "Student Activity Room 101"),
        ("多功能厅", "二楼", "需提前审批", "Multi-purpose Hall"),
        ("会议室 B", "办公区", "", "Meeting Room B"),
    ]
    conn.executemany(
        """
        UPDATE venues
        SET name = ?, location = ?, note = ?
        WHERE name = ?
        """,
        venue_updates,
    )


def get_dashboard() -> dict[str, Any]:
    with get_connection() as conn:
        items = conn.execute(
            f"""
            SELECT
                items.id,
                items.name,
                items.category,
                items.total_quantity,
                items.unit,
                items.location,
                items.size,
                items.note,
                COALESCE(SUM(
                    CASE WHEN {CURRENT_ACTIVE_LOAN_CONDITION} THEN loan_items.quantity ELSE 0 END
                ), 0) AS borrowed_quantity,
                items.total_quantity - COALESCE(SUM(
                    CASE WHEN {CURRENT_ACTIVE_LOAN_CONDITION} THEN loan_items.quantity ELSE 0 END
                ), 0) AS available_quantity
            FROM items
            LEFT JOIN loan_items ON loan_items.item_id = items.id
            LEFT JOIN loans ON loans.id = loan_items.loan_id
            GROUP BY items.id
            ORDER BY
                CASE items.name
                    WHEN '塑料椅' THEN 1
                    WHEN '折叠桌' THEN 2
                    WHEN '帐篷' THEN 3
                    WHEN '海报板' THEN 4
                    WHEN '拉杆音响' THEN 5
                    WHEN '小蜜蜂' THEN 6
                    WHEN '扩音器' THEN 7
                    WHEN '桌布' THEN 8
                    ELSE 99
                END,
                items.name
            """
        ).fetchall()

        loan_rows = conn.execute(
            """
            SELECT
                *
            FROM loans
            ORDER BY loans.created_at DESC, loans.id DESC
            """
        ).fetchall()
        loans = [build_loan_record(conn, row) for row in loan_rows]

        active_loans = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM loans
            WHERE {CURRENT_ACTIVE_LOAN_CONDITION}
            """
        ).fetchone()[0]

        low_stock = sum(1 for row in items if row["available_quantity"] <= 2)

        venue_booking_rows = conn.execute(
            """
            SELECT *
            FROM venue_bookings
            ORDER BY booking_date DESC, start_time DESC, id DESC
            """
        ).fetchall()
        venue_bookings = [get_venue_booking_record(conn, row["id"]) for row in venue_booking_rows]

        violation_records = conn.execute(
            """
            SELECT *
            FROM violation_records
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

    return {
        "items": [row_to_dict(row) for row in items],
        "loans": loans,
        "venue_bookings": venue_bookings,
        "violation_records": [row_to_dict(row) for row in violation_records],
        "stats": {
            "item_count": len(items),
            "venue_count": 1,
            "active_loans": active_loans,
            "low_stock": low_stock,
        },
    }


def get_loan_record(conn: sqlite3.Connection, loan_id: int) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT *
        FROM loans
        WHERE loans.id = ?
        """,
        (loan_id,),
    ).fetchone()
    if row is None:
        raise ValueError("借出记录不存在。")
    return build_loan_record(conn, row)


def get_available_quantity(
    conn: sqlite3.Connection,
    item_id: int,
    exclude_loan_id: int | None = None,
) -> int:
    item = conn.execute(
        "SELECT total_quantity FROM items WHERE id = ?",
        (item_id,),
    ).fetchone()
    if item is None:
        raise ValueError("选择的物资不存在。")

    borrowed = conn.execute(
        f"""
        SELECT COALESCE(SUM(loan_items.quantity), 0)
        FROM loan_items
        JOIN loans ON loans.id = loan_items.loan_id
        WHERE loan_items.item_id = ?
          AND {CURRENT_ACTIVE_LOAN_CONDITION}
          AND (? IS NULL OR loans.id != ?)
        """,
        (item_id, exclude_loan_id, exclude_loan_id),
    ).fetchone()[0]
    return int(item["total_quantity"]) - int(borrowed)


def get_loan_item_rows(conn: sqlite3.Connection, loan_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            loan_items.item_id,
            loan_items.quantity,
            items.name AS item_name,
            items.unit
        FROM loan_items
        JOIN items ON items.id = loan_items.item_id
        WHERE loan_items.loan_id = ?
        ORDER BY
            CASE items.name
                WHEN '塑料椅' THEN 1
                WHEN '折叠桌' THEN 2
                WHEN '帐篷' THEN 3
                WHEN '海报板' THEN 4
                WHEN '拉杆音响' THEN 5
                WHEN '小蜜蜂' THEN 6
                WHEN '扩音器' THEN 7
                WHEN '桌布' THEN 8
                ELSE 99
            END,
            items.name
        """,
        (loan_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def build_loan_record(conn: sqlite3.Connection, loan_row: sqlite3.Row) -> dict[str, Any]:
    loan = row_to_dict(loan_row)
    item_rows = get_loan_item_rows(conn, loan["id"])
    custom_quantity = int(loan.get("custom_item_quantity") or 0)
    custom_name = str(loan.get("custom_item_name") or "").strip()
    custom_unit = str(loan.get("custom_item_unit") or "件").strip() or "件"
    summary_parts = [
        f"{item['item_name']} × {item['quantity']} {item['unit']}"
        for item in item_rows
    ]

    if custom_name and custom_quantity > 0:
        summary_parts.append(f"{custom_name} × {custom_quantity} {custom_unit}")

    total_quantity = sum(int(item["quantity"]) for item in item_rows) + custom_quantity
    loan["loan_items"] = item_rows
    loan["item_summary"] = "、".join(summary_parts)
    loan["item_name"] = loan["item_summary"]
    loan["quantity"] = total_quantity
    loan["unit"] = "项" if len(summary_parts) > 1 else (item_rows[0]["unit"] if item_rows else custom_unit)
    loan["is_custom_item"] = len(item_rows) == 0 and bool(custom_name)
    return loan


def parse_positive_int(value: Any, field_name: str) -> int:
    try:
        number = int(value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name}必须是数字。") from exc
    if number < 0:
        raise ValueError(f"{field_name}不能小于 0。")
    return number


def parse_loan_item_payload(payload: dict[str, Any]) -> list[dict[str, int]]:
    item_quantities: dict[int, int] = {}
    raw_items = payload.get("loan_items")

    if isinstance(raw_items, list):
        for index, item in enumerate(raw_items, start=1):
            item_id_raw = item.get("item_id") if isinstance(item, dict) else None
            quantity = parse_positive_int(item.get("quantity") if isinstance(item, dict) else 0, f"第 {index} 项物资数量")
            if not item_id_raw or quantity == 0:
                continue
            item_id = int(item_id_raw)
            item_quantities[item_id] = item_quantities.get(item_id, 0) + quantity
    else:
        item_id_raw = payload.get("item_id")
        if item_id_raw and str(item_id_raw) != "other":
            quantity = parse_positive_int(payload.get("quantity"), "物资借用数量")
            if quantity > 0:
                item_quantities[int(item_id_raw)] = item_quantities.get(int(item_id_raw), 0) + quantity

    return [{"item_id": item_id, "quantity": quantity} for item_id, quantity in item_quantities.items()]


def get_item_id_by_name(conn: sqlite3.Connection, item_name: str) -> int:
    row = conn.execute("SELECT id FROM items WHERE name = ?", (item_name,)).fetchone()
    if row is None:
        raise ValueError(f"{item_name}未入库。")
    return int(row["id"])


def parse_venue_material_payload(conn: sqlite3.Connection, payload: dict[str, Any]) -> list[dict[str, int]]:
    material_fields = [
        ("折叠桌", "folding_table_quantity"),
        ("塑料椅", "plastic_chair_quantity"),
    ]
    loan_items = []
    for item_name, field_name in material_fields:
        quantity = parse_positive_int(payload.get(field_name), f"{item_name}借用数量")
        if quantity > 0:
            loan_items.append({
                "item_id": get_item_id_by_name(conn, item_name),
                "quantity": quantity,
            })
    return loan_items


def get_venue_material_quantities(conn: sqlite3.Connection, booking_id: int) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT items.name, loan_items.quantity
        FROM loans
        JOIN loan_items ON loan_items.loan_id = loans.id
        JOIN items ON items.id = loan_items.item_id
        WHERE loans.source_venue_booking_id = ?
        """,
        (booking_id,),
    ).fetchall()
    return {row["name"]: int(row["quantity"]) for row in rows}


def create_venue_material_loan(
    conn: sqlite3.Connection,
    booking_id: int,
    payload: dict[str, Any],
    booking_date: str,
    start_time: str,
    end_time: str,
    official_items: list[dict[str, int]],
) -> None:
    if not official_items:
        return

    for item in official_items:
        available_quantity = get_available_quantity(conn, item["item_id"])
        if item["quantity"] > available_quantity:
            item_row = conn.execute("SELECT name FROM items WHERE id = ?", (item["item_id"],)).fetchone()
            item_name = item_row["name"] if item_row else "所选物资"
            raise ValueError(f"{item_name}库存不足，无法为场地借用同步登记。")

    cursor = conn.execute(
        """
        INSERT INTO loans (
            borrower,
            department,
            contact,
            purpose,
            loan_date,
            loan_time,
            due_date,
            due_time,
            return_date,
            status,
            custom_item_name,
            custom_item_quantity,
            custom_item_unit,
            source_venue_booking_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(payload.get("borrower", "")).strip(),
            str(payload.get("department", "")).strip(),
            validate_phone(payload.get("contact")),
            f"场地借用同步物资：{str(payload.get('purpose', '')).strip() or '未填写'}",
            booking_date,
            start_time,
            booking_date,
            end_time,
            None,
            "Borrowed",
            "",
            0,
            "件",
            booking_id,
        ),
    )
    loan_id = cursor.lastrowid
    for item in official_items:
        conn.execute(
            "INSERT INTO loan_items (loan_id, item_id, quantity) VALUES (?, ?, ?)",
            (loan_id, item["item_id"], item["quantity"]),
        )


def max_borrowed_quantity_for_date(
    conn: sqlite3.Connection,
    item_id: int,
    date_value: str,
) -> int:
    rows = conn.execute(
        """
        SELECT
            loans.loan_date,
            loans.loan_time,
            loans.due_date,
            loans.due_time,
            loan_items.quantity
        FROM loan_items
        JOIN loans ON loans.id = loan_items.loan_id
        WHERE loan_items.item_id = ?
          AND loans.status = 'Borrowed'
          AND datetime(loans.loan_date || ' ' || loans.loan_time) <= datetime(? || ' 23:59')
          AND datetime(loans.due_date || ' ' || loans.due_time) > datetime(? || ' 00:00')
        """,
        (item_id, date_value, date_value),
    ).fetchall()
    if not rows:
        return 0

    day_start = datetime.fromisoformat(f"{date_value} 00:00")
    day_end = datetime.fromisoformat(f"{date_value} 23:59")
    events: list[tuple[datetime, int]] = []
    for row in rows:
        start_at = max(datetime.fromisoformat(f"{row['loan_date']} {row['loan_time']}"), day_start)
        end_at = min(datetime.fromisoformat(f"{row['due_date']} {row['due_time']}"), day_end)
        if start_at >= end_at:
            continue
        quantity = int(row["quantity"])
        events.append((start_at, quantity))
        events.append((end_at, -quantity))

    current_quantity = 0
    max_quantity = 0
    for _, delta in sorted(events, key=lambda event: (event[0], event[1])):
        current_quantity += delta
        max_quantity = max(max_quantity, current_quantity)
    return max_quantity


def get_inventory_snapshot(snapshot_date: str) -> dict[str, Any]:
    date_value = str(snapshot_date or "").strip()
    if not date_value:
        raise ValueError("请选择统计日期。")
    today_value = date.today().isoformat()

    with get_connection() as conn:
        if date_value == today_value:
            rows = conn.execute(
                f"""
                SELECT
                    items.id,
                    items.name,
                    items.category,
                    items.total_quantity,
                    items.unit,
                    items.size,
                    COALESCE(SUM(
                        CASE
                            WHEN {SNAPSHOT_CURRENT_LOAN_CONDITION}
                            THEN loan_items.quantity
                            ELSE 0
                        END
                    ), 0) AS borrowed_quantity,
                    items.total_quantity - COALESCE(SUM(
                        CASE
                            WHEN {SNAPSHOT_CURRENT_LOAN_CONDITION}
                            THEN loan_items.quantity
                            ELSE 0
                        END
                    ), 0) AS available_quantity
                FROM items
                LEFT JOIN loan_items ON loan_items.item_id = items.id
                LEFT JOIN loans ON loans.id = loan_items.loan_id
                GROUP BY items.id
                ORDER BY
                    CASE items.name
                        WHEN '塑料椅' THEN 1
                        WHEN '折叠桌' THEN 2
                        WHEN '帐篷' THEN 3
                        WHEN '海报板' THEN 4
                        WHEN '拉杆音响' THEN 5
                        WHEN '小蜜蜂' THEN 6
                        WHEN '扩音器' THEN 7
                        WHEN '桌布' THEN 8
                        ELSE 99
                    END,
                    items.name
                """
            ).fetchall()
            items = [row_to_dict(row) for row in rows]
        else:
            rows = conn.execute(
                """
            SELECT
                items.id,
                items.name,
                items.category,
                items.total_quantity,
                items.unit,
                items.size
            FROM items
            ORDER BY
                CASE items.name
                    WHEN '塑料椅' THEN 1
                    WHEN '折叠桌' THEN 2
                    WHEN '帐篷' THEN 3
                    WHEN '海报板' THEN 4
                    WHEN '拉杆音响' THEN 5
                    WHEN '小蜜蜂' THEN 6
                    WHEN '扩音器' THEN 7
                    WHEN '桌布' THEN 8
                    ELSE 99
                END,
                items.name
            """,
            ).fetchall()
            items = []
            for row in rows:
                item = row_to_dict(row)
                borrowed_quantity = max_borrowed_quantity_for_date(conn, int(item["id"]), date_value)
                item["borrowed_quantity"] = borrowed_quantity
                item["available_quantity"] = int(item["total_quantity"]) - borrowed_quantity
                items.append(item)

    return {
        "date": date_value,
        "items": items,
        "total_available": sum(row["available_quantity"] for row in items),
        "total_borrowed": sum(row["borrowed_quantity"] for row in items),
    }


def get_item_inventory_trend(item_id: int, start_date: str, days: int = 10) -> dict[str, Any]:
    start = parse_date(start_date, "起始日期")
    day_count = max(1, min(int(days or 10), 31))

    with get_connection() as conn:
        item = conn.execute(
            """
            SELECT id, name, total_quantity, unit, size
            FROM items
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
        if item is None:
            raise ValueError("物资不存在。")

        total_quantity = int(item["total_quantity"])
        trend = []
        today_value = date.today().isoformat()
        for offset in range(day_count):
            current_date = start + timedelta(days=offset)
            date_value = current_date.isoformat()
            if date_value == today_value:
                borrowed_quantity = conn.execute(
                    f"""
                    SELECT COALESCE(SUM(loan_items.quantity), 0)
                    FROM loan_items
                    JOIN loans ON loans.id = loan_items.loan_id
                    WHERE loan_items.item_id = ?
                      AND {SNAPSHOT_CURRENT_LOAN_CONDITION}
                    """,
                    (item_id,),
                ).fetchone()[0]
                borrowed_quantity = int(borrowed_quantity)
            else:
                borrowed_quantity = max_borrowed_quantity_for_date(conn, item_id, date_value)
            trend.append(
                {
                    "date": date_value,
                    "available_quantity": total_quantity - borrowed_quantity,
                    "borrowed_quantity": borrowed_quantity,
                    "total_quantity": total_quantity,
                }
            )

    return {
        "item": row_to_dict(item),
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=day_count - 1)).isoformat(),
        "days": trend,
    }


def add_item(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("请填写物资名称。")

    total_quantity = int(payload.get("total_quantity") or 0)
    if total_quantity < 0:
        raise ValueError("物资总数量不能小于 0。")

    size = str(payload.get("size", "")).strip() or "无"

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO items (name, category, total_quantity, unit, location, size, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                str(payload.get("category", "通用")).strip() or "通用",
                total_quantity,
                str(payload.get("unit", "件")).strip() or "件",
                str(payload.get("location", "")).strip(),
                size,
                str(payload.get("note", "")).strip(),
            ),
        )
        item = conn.execute("SELECT * FROM items WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(item)


def update_item(item_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("请填写物资名称。")

    total_quantity = int(payload.get("total_quantity") or 0)
    if total_quantity < 0:
        raise ValueError("物资总数量不能小于 0。")

    size = str(payload.get("size", "")).strip() or "无"

    with get_connection() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if item is None:
            raise ValueError("物资不存在。")

        category = str(payload.get("category", item["category"])).strip() or item["category"] or "通用"
        location = str(payload.get("location", item["location"])).strip()
        note = str(payload.get("note", item["note"])).strip()

        borrowed_quantity = conn.execute(
            f"""
            SELECT COALESCE(SUM(loan_items.quantity), 0)
            FROM loan_items
            JOIN loans ON loans.id = loan_items.loan_id
            WHERE loan_items.item_id = ?
              AND {CURRENT_ACTIVE_LOAN_CONDITION}
            """,
            (item_id,),
        ).fetchone()[0]
        if total_quantity < int(borrowed_quantity):
            raise ValueError("总数量不能小于当前借出中的数量。")

        conn.execute(
            """
            UPDATE items
            SET name = ?,
                category = ?,
                total_quantity = ?,
                unit = ?,
                location = ?,
                size = ?,
                note = ?
            WHERE id = ?
            """,
            (
                name,
                category,
                total_quantity,
                str(payload.get("unit", "件")).strip() or "件",
                location,
                size,
                note,
                item_id,
            ),
        )
        updated = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return row_to_dict(updated)


def add_venue(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("请填写场地名称。")

    capacity = int(payload.get("capacity") or 0)
    if capacity < 0:
        raise ValueError("容纳人数不能小于 0。")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO venues (name, capacity, location, status, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                capacity,
                str(payload.get("location", "")).strip(),
                str(payload.get("status", "Available")).strip() or "Available",
                str(payload.get("note", "")).strip(),
            ),
        )
        venue = conn.execute("SELECT * FROM venues WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(venue)


def create_loan(payload: dict[str, Any]) -> dict[str, Any]:
    borrower = str(payload.get("borrower", "")).strip()
    if not borrower:
        raise ValueError("请填写借用人。")

    contact = validate_phone(payload.get("contact"))
    official_items = parse_loan_item_payload(payload)
    custom_item_name = str(payload.get("custom_item_name", "")).strip()
    custom_quantity = parse_positive_int(
        payload.get("custom_item_quantity", payload.get("quantity") if str(payload.get("item_id")) == "other" else 0),
        "手动其他物资数量",
    )
    if custom_quantity > 0 and not custom_item_name:
        raise ValueError("请填写手动其他物资名称。")
    if custom_item_name and custom_quantity == 0:
        raise ValueError("请填写手动其他物资数量。")
    if not official_items and custom_quantity == 0:
        raise ValueError("请至少填写一种借用物资。")

    status = "Borrowed"
    loan_time = validate_material_time(payload.get("loan_time"), "借用时间")
    due_time = validate_material_time(payload.get("due_time"), "归还时间")

    with get_connection() as conn:
        for item in official_items:
            available_quantity = get_available_quantity(conn, item["item_id"])
            if item["quantity"] > available_quantity:
                item_row = conn.execute("SELECT name FROM items WHERE id = ?", (item["item_id"],)).fetchone()
                item_name = item_row["name"] if item_row else "所选物资"
                raise ValueError(f"{item_name}库存不足，无法借出这么多。")

        cursor = conn.execute(
            """
            INSERT INTO loans (
                borrower,
                department,
                contact,
                purpose,
                loan_date,
                loan_time,
                due_date,
                due_time,
                return_date,
                status,
                custom_item_name,
                custom_item_quantity,
                custom_item_unit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                borrower,
                str(payload.get("department", "")).strip(),
                contact,
                str(payload.get("purpose", "")).strip(),
                str(payload.get("loan_date", "")).strip(),
                loan_time,
                str(payload.get("due_date", "")).strip(),
                due_time,
                None,
                status,
                custom_item_name,
                custom_quantity,
                "件",
            ),
        )
        loan_id = cursor.lastrowid

        for item in official_items:
            conn.execute(
                "INSERT INTO loan_items (loan_id, item_id, quantity) VALUES (?, ?, ?)",
                (loan_id, item["item_id"], item["quantity"]),
            )

        loan = get_loan_record(conn, loan_id)

    return loan


def update_loan(loan_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    borrower = str(payload.get("borrower", "")).strip()
    if not borrower:
        raise ValueError("请填写借用人。")

    contact = validate_phone(payload.get("contact"))
    official_items = parse_loan_item_payload(payload)
    custom_item_name = str(payload.get("custom_item_name", "")).strip()
    custom_quantity = parse_positive_int(
        payload.get("custom_item_quantity", payload.get("quantity") if str(payload.get("item_id")) == "other" else 0),
        "手动其他物资数量",
    )
    if custom_quantity > 0 and not custom_item_name:
        raise ValueError("请填写手动其他物资名称。")
    if custom_item_name and custom_quantity == 0:
        raise ValueError("请填写手动其他物资数量。")
    if not official_items and custom_quantity == 0:
        raise ValueError("请至少填写一种借用物资。")

    loan_time = validate_material_time(payload.get("loan_time"), "借用时间")
    due_time = validate_material_time(payload.get("due_time"), "归还时间")

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM loans WHERE id = ?",
            (loan_id,),
        ).fetchone()
        if existing is None:
            raise ValueError("借出记录不存在。")

        for item in official_items:
            available_quantity = get_available_quantity(conn, item["item_id"], loan_id)
            if item["quantity"] > available_quantity:
                item_row = conn.execute("SELECT name FROM items WHERE id = ?", (item["item_id"],)).fetchone()
                item_name = item_row["name"] if item_row else "所选物资"
                raise ValueError(f"{item_name}库存不足，无法借出这么多。")

        conn.execute(
            """
            UPDATE loans
            SET borrower = ?,
                department = ?,
                contact = ?,
                purpose = ?,
                loan_date = ?,
                loan_time = ?,
                due_date = ?,
                due_time = ?,
                return_date = ?,
                status = ?,
                custom_item_name = ?,
                custom_item_quantity = ?,
                custom_item_unit = ?
            WHERE id = ?
            """,
            (
                borrower,
                str(payload.get("department", "")).strip(),
                contact,
                str(payload.get("purpose", "")).strip(),
                str(payload.get("loan_date", "")).strip(),
                loan_time,
                str(payload.get("due_date", "")).strip(),
                due_time,
                None,
                "Borrowed",
                custom_item_name,
                custom_quantity,
                "件",
                loan_id,
            ),
        )
        conn.execute("DELETE FROM loan_items WHERE loan_id = ?", (loan_id,))
        for item in official_items:
            conn.execute(
                "INSERT INTO loan_items (loan_id, item_id, quantity) VALUES (?, ?, ?)",
                (loan_id, item["item_id"], item["quantity"]),
            )
        return get_loan_record(conn, loan_id)


def delete_loan(loan_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        get_loan_record(conn, loan_id)
        conn.execute("DELETE FROM loans WHERE id = ?", (loan_id,))
    return {"deleted": True, "id": loan_id}


def get_venue_booking_record(conn: sqlite3.Connection, booking_id: int) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM venue_bookings WHERE id = ?",
        (booking_id,),
    ).fetchone()
    if row is None:
        raise ValueError("场地借用记录不存在。")
    booking = row_to_dict(row)
    material_quantities = get_venue_material_quantities(conn, booking_id)
    booking["folding_table_quantity"] = material_quantities.get("折叠桌", 0)
    booking["plastic_chair_quantity"] = material_quantities.get("塑料椅", 0)
    return booking


def validate_booking_time(start_time: str, end_time: str) -> None:
    if not start_time or not end_time:
        raise ValueError("请填写场地借用的开始和结束时间。")
    if start_time >= end_time:
        raise ValueError("结束时间必须晚于开始时间。")
    if (start_time, end_time) not in VENUE_TIME_SLOTS:
        raise ValueError("场地借用时间只能选择 08:00~12:00、14:00~17:00、19:00~22:00。")


def parse_booking_time_slots(payload: dict[str, Any]) -> list[tuple[str, str]]:
    raw_slots = payload.get("time_slots")
    if raw_slots is None:
        start_time = str(payload.get("start_time", "")).strip()
        end_time = str(payload.get("end_time", "")).strip()
        raw_slots = [f"{start_time}|{end_time}"] if start_time or end_time else []
    if isinstance(raw_slots, str):
        raw_slots = [raw_slots]
    if not isinstance(raw_slots, list):
        raise ValueError("请选择场地借用时间段。")

    time_slots: list[tuple[str, str]] = []
    seen_slots: set[tuple[str, str]] = set()
    for raw_slot in raw_slots:
        parts = str(raw_slot or "").split("|", 1)
        if len(parts) != 2:
            raise ValueError("场地借用时间段格式不正确。")
        start_time = parts[0].strip()
        end_time = parts[1].strip()
        validate_booking_time(start_time, end_time)
        slot = (start_time, end_time)
        if slot not in seen_slots:
            seen_slots.add(slot)
            time_slots.append(slot)

    if not time_slots:
        raise ValueError("请至少选择一个场地借用时间段。")
    return time_slots


def ensure_no_booking_conflict(
    conn: sqlite3.Connection,
    booking_date: str,
    start_time: str,
    end_time: str,
    exclude_booking_id: int | None = None,
) -> None:
    conflict = conn.execute(
        """
        SELECT 1
        FROM venue_bookings
        WHERE booking_date = ?
          AND status = 'Booked'
          AND (? IS NULL OR id != ?)
          AND NOT (end_time <= ? OR start_time >= ?)
        LIMIT 1
        """,
        (booking_date, exclude_booking_id, exclude_booking_id, start_time, end_time),
    ).fetchone()
    if conflict:
        raise ValueError("该时间段已有场地借用记录。")


def create_venue_booking(payload: dict[str, Any]) -> dict[str, Any]:
    borrower = str(payload.get("borrower", "")).strip()
    if not borrower:
        raise ValueError("请填写借用人。")

    department = str(payload.get("department", "")).strip()
    contact = validate_phone(payload.get("contact"))
    setup_time = str(payload.get("setup_time", "")).strip()
    estimated_attendance = parse_positive_int(payload.get("estimated_attendance"), "估计到场人数")

    booking_date = str(payload.get("booking_date", "")).strip()
    if not booking_date:
        raise ValueError("请选择场地借用日期。")

    time_slots = parse_booking_time_slots(payload)

    with get_connection() as conn:
        venue_loan_items = parse_venue_material_payload(conn, payload)
        for start_time, end_time in time_slots:
            ensure_no_booking_conflict(conn, booking_date, start_time, end_time)

        created_bookings = []
        for start_time, end_time in time_slots:
            cursor = conn.execute(
                """
                INSERT INTO venue_bookings (
                    borrower,
                    department,
                    contact,
                    purpose,
                    setup_time,
                    estimated_attendance,
                    booking_date,
                    start_time,
                    end_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    borrower,
                    department,
                    contact,
                    str(payload.get("purpose", "")).strip(),
                    setup_time,
                    estimated_attendance,
                    booking_date,
                    start_time,
                    end_time,
                ),
            )
            booking_id = cursor.lastrowid
            create_venue_material_loan(
                conn,
                booking_id,
                payload,
                booking_date,
                start_time,
                end_time,
                venue_loan_items,
            )
            created_bookings.append(get_venue_booking_record(conn, booking_id))

        return {
            **created_bookings[0],
            "bookings": created_bookings,
            "created_count": len(created_bookings),
        }


def update_venue_booking(booking_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    borrower = str(payload.get("borrower", "")).strip()
    if not borrower:
        raise ValueError("请填写借用人。")

    department = str(payload.get("department", "")).strip()
    contact = validate_phone(payload.get("contact"))
    setup_time = str(payload.get("setup_time", "")).strip()
    estimated_attendance = parse_positive_int(payload.get("estimated_attendance"), "估计到场人数")

    booking_date = str(payload.get("booking_date", "")).strip()
    if not booking_date:
        raise ValueError("请选择场地借用日期。")

    time_slots = parse_booking_time_slots(payload)
    if len(time_slots) != 1:
        raise ValueError("修改场地借用时只能选择一个时间段。")
    start_time, end_time = time_slots[0]

    status = str(payload.get("status", "Booked")).strip() or "Booked"
    if status not in {"Booked", "Cancelled"}:
        raise ValueError("场地借用状态不正确。")

    with get_connection() as conn:
        get_venue_booking_record(conn, booking_id)
        venue_loan_items = parse_venue_material_payload(conn, payload)
        if status == "Booked":
            ensure_no_booking_conflict(conn, booking_date, start_time, end_time, booking_id)

        conn.execute(
            """
            UPDATE venue_bookings
            SET borrower = ?,
                department = ?,
                contact = ?,
                purpose = ?,
                setup_time = ?,
                estimated_attendance = ?,
                booking_date = ?,
                start_time = ?,
                end_time = ?,
                status = ?
            WHERE id = ?
            """,
            (
                borrower,
                department,
                contact,
                str(payload.get("purpose", "")).strip(),
                setup_time,
                estimated_attendance,
                booking_date,
                start_time,
                end_time,
                status,
                booking_id,
            ),
        )
        conn.execute("DELETE FROM loans WHERE source_venue_booking_id = ?", (booking_id,))
        create_venue_material_loan(
            conn,
            booking_id,
            payload,
            booking_date,
            start_time,
            end_time,
            venue_loan_items,
        )
        return get_venue_booking_record(conn, booking_id)


def delete_venue_booking(booking_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        get_venue_booking_record(conn, booking_id)
        conn.execute("DELETE FROM loans WHERE source_venue_booking_id = ?", (booking_id,))
        conn.execute("DELETE FROM venue_bookings WHERE id = ?", (booking_id,))
    return {"deleted": True, "id": booking_id}


def create_violation_record(payload: dict[str, Any]) -> dict[str, Any]:
    borrower = str(payload.get("borrower", "")).strip()
    if not borrower:
        raise ValueError("请填写借用人。")

    contact = validate_phone(payload.get("contact"))
    damaged_item = str(payload.get("damaged_item", "")).strip()
    if not damaged_item:
        raise ValueError("请填写损坏物资。")

    resolution = str(payload.get("resolution", "")).strip()
    if not resolution:
        raise ValueError("请填写处理办法。")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO violation_records (
                borrower,
                department,
                contact,
                damaged_item,
                resolution
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                borrower,
                str(payload.get("department", "")).strip(),
                contact,
                damaged_item,
                resolution,
            ),
        )
        record = conn.execute(
            "SELECT * FROM violation_records WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

    return row_to_dict(record)


def delete_violation_record(record_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        record = conn.execute(
            "SELECT id FROM violation_records WHERE id = ?",
            (record_id,),
        ).fetchone()
        if record is None:
            raise ValueError("违规记录不存在。")
        conn.execute("DELETE FROM violation_records WHERE id = ?", (record_id,))
    return {"deleted": True, "id": record_id}


def safe_original_filename(filename: str) -> str:
    name = str(filename or "").strip().replace("\\", "/").split("/")[-1]
    name = SAFE_FILENAME_PATTERN.sub("_", name).strip("._ ")
    if not name:
        raise ValueError("文件名不正确。")
    return name[:120]


def document_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def public_user(row: sqlite3.Row) -> dict[str, Any]:
    is_admin = row["username"] == DEFAULT_LOGIN_USERNAME
    return {
        "id": row["id"],
        "username": row["username"],
        "student_id": row["student_id"] or row["username"],
        "phone": row["phone"] or "",
        "display_name": row["display_name"] or row["username"],
        "is_admin": is_admin,
        "approval_status": row["approval_status"] or "approved",
        "created_at": row["created_at"],
    }


def create_registered_user(payload: dict[str, Any]) -> dict[str, Any]:
    student_id = validate_student_id(payload.get("student_id") or payload.get("username"))
    display_name = str(payload.get("display_name") or payload.get("name") or "").strip()
    if not display_name:
        raise ValueError("请填写姓名。")
    if len(display_name) > 20:
        raise ValueError("姓名不能超过 20 个字。")
    phone = validate_phone(payload.get("phone"))
    password = str(payload.get("password") or "")
    confirm_password = str(payload.get("confirm_password") or "")
    if len(password) < 6:
        raise ValueError("密码至少需要 6 位。")
    if password != confirm_password:
        raise ValueError("两次输入的密码不一致。")

    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
               OR student_id = ?
            """,
            (student_id, student_id),
        ).fetchone()
        if existing:
            raise ValueError("这个学号已经注册。")

        cursor = conn.execute(
            """
            INSERT INTO users (username, student_id, phone, approval_status, password_hash, display_name)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                student_id,
                phone,
                "pending",
                generate_password_hash(password),
                display_name,
            ),
        )
        user = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()

    return public_user(user)


def authenticate_user(username: Any, password: Any) -> dict[str, Any]:
    username_value = str(username or "").strip()
    password_value = str(password or "")
    if not username_value or not password_value:
        raise ValueError("请填写账号和密码。")

    with get_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username_value,),
        ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password_value):
        raise ValueError("账号或密码不正确。")
    if user["approval_status"] != "approved":
        raise ValueError("账号正在等待管理员审核。")
    return public_user(user)


def get_user_by_id(user_id: Any) -> dict[str, Any] | None:
    try:
        user_id_value = int(user_id)
    except (TypeError, ValueError):
        return None

    with get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id_value,)).fetchone()
    return public_user(user) if user else None


def list_users() -> dict[str, Any]:
    with get_connection() as conn:
        users = conn.execute(
            """
            SELECT *
            FROM users
            ORDER BY username = ? DESC, created_at DESC, id DESC
            """,
            (DEFAULT_LOGIN_USERNAME,),
        ).fetchall()
    return {"users": [public_user(row) for row in users]}


def update_user(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise ValueError("用户不存在。")
        if user["username"] == DEFAULT_LOGIN_USERNAME:
            raise ValueError("管理员账号不能修改。")

        student_id = validate_student_id(payload.get("student_id") or payload.get("username"))
        display_name = str(payload.get("display_name") or payload.get("name") or "").strip()
        if not display_name:
            raise ValueError("请填写姓名。")
        if len(display_name) > 20:
            raise ValueError("姓名不能超过 20 个字。")
        phone = validate_phone(payload.get("phone"))
        password = str(payload.get("password") or "")
        existing = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id <> ?
              AND (username = ? OR student_id = ?)
            """,
            (user_id, student_id, student_id),
        ).fetchone()
        if existing:
            raise ValueError("这个学号已经被其他用户使用。")

        if password:
            if len(password) < 6:
                raise ValueError("密码至少需要 6 位。")
            conn.execute(
                """
                UPDATE users
                SET username = ?,
                    student_id = ?,
                    phone = ?,
                    password_hash = ?,
                    display_name = ?
                WHERE id = ?
                """,
                (
                    student_id,
                    student_id,
                    phone,
                    generate_password_hash(password),
                    display_name,
                    user_id,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE users
                SET username = ?,
                    student_id = ?,
                    phone = ?,
                    display_name = ?
                WHERE id = ?
                """,
                (
                    student_id,
                    student_id,
                    phone,
                    display_name,
                    user_id,
                ),
            )

        updated = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return public_user(updated)


def approve_user(user_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise ValueError("用户不存在。")
        if user["username"] == DEFAULT_LOGIN_USERNAME:
            raise ValueError("管理员账号不需要审核。")
        conn.execute(
            "UPDATE users SET approval_status = 'approved' WHERE id = ?",
            (user_id,),
        )
        approved = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return public_user(approved)


def delete_user(user_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise ValueError("用户不存在。")
        if user["username"] == DEFAULT_LOGIN_USERNAME:
            raise ValueError("管理员账号不能删除。")
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return {"deleted": True, "id": user_id}


def repository_folder_with_counts(conn: sqlite3.Connection, folder_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT
            repository_folders.*,
            (
                SELECT COUNT(*)
                FROM repository_folders AS child_folders
                WHERE child_folders.parent_id = repository_folders.id
            ) AS folder_count,
            (
                SELECT COUNT(*)
                FROM repository_documents
                WHERE repository_documents.folder_id = repository_folders.id
            ) AS document_count
        FROM repository_folders
        WHERE repository_folders.id = ?
        """,
        (folder_id,),
    ).fetchone()


def repository_breadcrumbs(conn: sqlite3.Connection, folder_id: int) -> list[dict[str, Any]]:
    breadcrumbs: list[dict[str, Any]] = []
    visited: set[int] = set()
    current_id: int | None = folder_id

    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        folder = conn.execute(
            "SELECT id, name, parent_id FROM repository_folders WHERE id = ?",
            (current_id,),
        ).fetchone()
        if folder is None:
            break
        breadcrumbs.append(row_to_dict(folder))
        current_id = folder["parent_id"]

    breadcrumbs.reverse()
    return breadcrumbs


def resolve_repository_folder_id(conn: sqlite3.Connection, folder_id: Any = None) -> int:
    root_id = ensure_repository_root(conn)
    folder_id_text = str(folder_id or "").strip()
    if not folder_id_text or folder_id_text == "0":
        return root_id

    try:
        target_id = int(folder_id_text)
    except ValueError as exc:
        raise ValueError("文件夹不存在。") from exc

    folder = conn.execute("SELECT id FROM repository_folders WHERE id = ?", (target_id,)).fetchone()
    if folder is None:
        raise ValueError("文件夹不存在。")
    return target_id


def get_document_library(folder_id: Any = None) -> dict[str, Any]:
    with get_connection() as conn:
        root_id = ensure_repository_root(conn)
        current_folder_id = resolve_repository_folder_id(conn, folder_id)
        current_folder = repository_folder_with_counts(conn, current_folder_id)
        if current_folder is None:
            raise ValueError("文件夹不存在。")
        folders = conn.execute(
            """
            SELECT
                repository_folders.*,
                (
                    SELECT COUNT(*)
                    FROM repository_folders AS child_folders
                    WHERE child_folders.parent_id = repository_folders.id
                ) AS folder_count,
                (
                    SELECT COUNT(*)
                    FROM repository_documents
                    WHERE repository_documents.folder_id = repository_folders.id
                ) AS document_count
            FROM repository_folders
            WHERE repository_folders.parent_id = ?
            ORDER BY repository_folders.name COLLATE NOCASE ASC, repository_folders.id ASC
            """,
            (current_folder_id,),
        ).fetchall()
        documents = conn.execute(
            """
            SELECT
                repository_documents.*,
                repository_folders.name AS folder_name
            FROM repository_documents
            JOIN repository_folders ON repository_folders.id = repository_documents.folder_id
            WHERE repository_documents.folder_id = ?
            ORDER BY repository_documents.original_name COLLATE NOCASE ASC, repository_documents.id ASC
            """,
            (current_folder_id,),
        ).fetchall()
        breadcrumbs = repository_breadcrumbs(conn, current_folder_id)

    return {
        "root_id": root_id,
        "current_folder": row_to_dict(current_folder),
        "breadcrumbs": breadcrumbs,
        "folders": [row_to_dict(row) for row in folders],
        "documents": [row_to_dict(row) for row in documents],
    }


def create_repository_folder(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("请填写文件夹名称。")
    if name in {".", ".."}:
        raise ValueError("文件夹名称不正确。")
    if len(name) > 40:
        raise ValueError("文件夹名称不能超过 40 个字。")

    with get_connection() as conn:
        parent_id = resolve_repository_folder_id(conn, payload.get("parent_id"))
        existing = conn.execute(
            """
            SELECT id
            FROM repository_folders
            WHERE parent_id = ?
              AND name = ?
            """,
            (parent_id, name),
        ).fetchone()
        if existing:
            raise ValueError("当前文件夹里已经有同名文件夹。")
        try:
            cursor = conn.execute(
                "INSERT INTO repository_folders (name, parent_id) VALUES (?, ?)",
                (name, parent_id),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("文件夹名称已存在。") from exc
        folder = repository_folder_with_counts(conn, cursor.lastrowid)

    return row_to_dict(folder)


def delete_repository_folder(folder_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        root_id = ensure_repository_root(conn)
        if int(folder_id) == int(root_id):
            raise ValueError("根目录不能删除。")
        folder = conn.execute("SELECT * FROM repository_folders WHERE id = ?", (folder_id,)).fetchone()
        if folder is None:
            raise ValueError("文件夹不存在。")
        child_folder_count = conn.execute(
            "SELECT COUNT(*) FROM repository_folders WHERE parent_id = ?",
            (folder_id,),
        ).fetchone()[0]
        document_count = conn.execute(
            "SELECT COUNT(*) FROM repository_documents WHERE folder_id = ?",
            (folder_id,),
        ).fetchone()[0]
        if child_folder_count or document_count:
            raise ValueError("请先删除文件夹里的内容。")
        conn.execute("DELETE FROM repository_folders WHERE id = ?", (folder_id,))
    return {"deleted": True, "id": folder_id, "parent_id": folder["parent_id"]}


def create_repository_document(folder_id: int, uploaded_file: Any) -> dict[str, Any]:
    if uploaded_file is None or not getattr(uploaded_file, "filename", ""):
        raise ValueError("请选择要上传的文档。")

    original_name = safe_original_filename(uploaded_file.filename)
    extension = document_extension(original_name)
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValueError("暂不支持上传这种文件类型。")
    stored_name = f"{uuid.uuid4().hex}{extension}"
    target_path = uploads_dir() / stored_name

    with get_connection() as conn:
        folder = conn.execute("SELECT id FROM repository_folders WHERE id = ?", (folder_id,)).fetchone()
        if folder is None:
            raise ValueError("文件夹不存在。")

    uploaded_file.save(target_path)
    file_size = target_path.stat().st_size
    if file_size > MAX_UPLOAD_SIZE:
        target_path.unlink(missing_ok=True)
        raise ValueError("单个文件不能超过 25MB。")

    mime_type = uploaded_file.mimetype or mimetypes.guess_type(original_name)[0] or "application/octet-stream"

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO repository_documents (
                folder_id,
                original_name,
                stored_name,
                mime_type,
                file_size
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (folder_id, original_name, stored_name, mime_type, file_size),
        )
        document = conn.execute(
            """
            SELECT
                repository_documents.*,
                repository_folders.name AS folder_name
            FROM repository_documents
            JOIN repository_folders ON repository_folders.id = repository_documents.folder_id
            WHERE repository_documents.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return row_to_dict(document)


def get_repository_document(document_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        document = conn.execute(
            """
            SELECT
                repository_documents.*,
                repository_folders.name AS folder_name
            FROM repository_documents
            JOIN repository_folders ON repository_folders.id = repository_documents.folder_id
            WHERE repository_documents.id = ?
            """,
            (document_id,),
        ).fetchone()
        if document is None:
            raise ValueError("文档不存在。")
    return row_to_dict(document)


def repository_document_path(document: dict[str, Any]) -> Path:
    path = uploads_dir() / str(document["stored_name"])
    if not path.exists():
        raise ValueError("文档文件不存在。")
    return path


def delete_repository_document(document_id: int) -> dict[str, Any]:
    document = get_repository_document(document_id)
    path = uploads_dir() / str(document["stored_name"])

    with get_connection() as conn:
        conn.execute("DELETE FROM repository_documents WHERE id = ?", (document_id,))

    path.unlink(missing_ok=True)
    return {"deleted": True, "id": document_id}
