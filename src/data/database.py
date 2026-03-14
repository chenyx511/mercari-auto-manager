import sqlite3
import os
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'mercari.db')


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            price INTEGER NOT NULL,
            original_price INTEGER,
            condition TEXT DEFAULT '目立った傷や汚れなし',
            shipping_payer TEXT DEFAULT '送料込み(出品者負担)',
            shipping_method TEXT,
            shipping_area TEXT,
            shipping_days TEXT DEFAULT '1~2日で発送',
            images TEXT,  -- JSON array of image paths
            status TEXT DEFAULT 'pending',  -- pending, listed, sold, deleted
            mercari_id TEXT,
            listed_at TIMESTAMP,
            last_price_update TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            old_price INTEGER NOT NULL,
            new_price INTEGER NOT NULL,
            reason TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            mercari_product_id TEXT,
            buyer_message TEXT,
            reply_message TEXT,
            replied_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL,  -- listing, pricing, reply
            product_id INTEGER,
            details TEXT,
            status TEXT DEFAULT 'success',  -- success, failed
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()


class ProductRepository:

    @staticmethod
    def add(product: dict) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products (title, description, category, price, original_price,
                                  condition, shipping_payer, shipping_method,
                                  shipping_area, shipping_days, images, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product.get('title'), product.get('description'),
            product.get('category'), product.get('price'),
            product.get('price'),
            product.get('condition', '目立った傷や汚れなし'),
            product.get('shipping_payer', '送料込み(出品者負担)'),
            product.get('shipping_method'),
            product.get('shipping_area'),
            product.get('shipping_days', '1~2日で発送'),
            product.get('images'), 'pending'
        ))
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return product_id

    @staticmethod
    def update_status(product_id: int, status: str, mercari_id: str = None):
        conn = get_connection()
        now = datetime.now().isoformat()
        if mercari_id:
            conn.execute(
                "UPDATE products SET status=?, mercari_id=?, listed_at=?, updated_at=? WHERE id=?",
                (status, mercari_id, now, now, product_id)
            )
        else:
            conn.execute(
                "UPDATE products SET status=?, updated_at=? WHERE id=?",
                (status, now, product_id)
            )
        conn.commit()
        conn.close()

    @staticmethod
    def update_price(product_id: int, new_price: int, reason: str = ""):
        conn = get_connection()
        now = datetime.now().isoformat()
        row = conn.execute("SELECT price FROM products WHERE id=?", (product_id,)).fetchone()
        if row:
            old_price = row['price']
            conn.execute(
                "UPDATE products SET price=?, last_price_update=?, updated_at=? WHERE id=?",
                (new_price, now, now, product_id)
            )
            conn.execute(
                "INSERT INTO price_history (product_id, old_price, new_price, reason) VALUES (?, ?, ?, ?)",
                (product_id, old_price, new_price, reason)
            )
        conn.commit()
        conn.close()

    @staticmethod
    def get_all(status: str = None) -> list:
        conn = get_connection()
        if status:
            rows = conn.execute(
                "SELECT * FROM products WHERE status=? ORDER BY created_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM products ORDER BY created_at DESC"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(product_id: int) -> dict | None:
        conn = get_connection()
        row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_listed_products() -> list:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM products WHERE status='listed' ORDER BY listed_at ASC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_price_history(product_id: int) -> list:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM price_history WHERE product_id=? ORDER BY changed_at DESC",
            (product_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def delete(product_id: int):
        conn = get_connection()
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def count_by_status() -> dict:
        conn = get_connection()
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM products GROUP BY status"
        ).fetchall()
        conn.close()
        return {r['status']: r['cnt'] for r in rows}


class MessageRepository:

    @staticmethod
    def add(message: dict) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (product_id, mercari_product_id, buyer_message,
                                  reply_message, replied_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            message.get('product_id'), message.get('mercari_product_id'),
            message.get('buyer_message'), message.get('reply_message'),
            message.get('replied_at')
        ))
        msg_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return msg_id

    @staticmethod
    def get_recent(limit: int = 50) -> list:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM messages ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


class OperationLogRepository:

    @staticmethod
    def add(op_type: str, product_id: int = None, details: str = "",
            status: str = "success", error_message: str = ""):
        conn = get_connection()
        conn.execute("""
            INSERT INTO operation_logs (operation_type, product_id, details, status, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, (op_type, product_id, details, status, error_message))
        conn.commit()
        conn.close()

    @staticmethod
    def get_recent(limit: int = 100) -> list:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM operation_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
