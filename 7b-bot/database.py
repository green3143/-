import sqlite3
from contextlib import contextmanager

DB_PATH = "bot_data.db"

def init_db():
    """Создаёт таблицы при первом запуске."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Таблица призов (розыгрышей)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price_stars INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица участников (кто оплатил)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prize_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                charge_id TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prize_id) REFERENCES prizes(id)
            )
        """)
        
        # Таблица выученных фраз (для режима чуши)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_phrases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phrase TEXT NOT NULL UNIQUE
            )
        """)
        
        conn.commit()

@contextmanager
def get_db():
    """Контекстный менеджер для подключения к БД."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ---------- РАБОТА С ПРИЗАМИ ----------
def create_prize(title: str, price_stars: int) -> int:
    """Создаёт новый приз, возвращает его ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO prizes (title, price_stars) VALUES (?, ?)",
            (title, price_stars)
        )
        conn.commit()
        return cursor.lastrowid

def get_active_prizes():
    """Возвращает список активных призов."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prizes WHERE is_active = 1 ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_prize_by_id(prize_id: int):
    """Возвращает приз по ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prizes WHERE id = ?", (prize_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def deactivate_prize(prize_id: int):
    """Закрывает приз (больше нельзя участвовать)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE prizes SET is_active = 0 WHERE id = ?", (prize_id,))
        conn.commit()

# ---------- РАБОТА С УЧАСТНИКАМИ ----------
def add_participant(prize_id: int, user_id: int, username: str, first_name: str, charge_id: str):
    """Добавляет оплатившего участника."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Проверяем, не участвует ли уже
        cursor.execute(
            "SELECT id FROM participants WHERE prize_id = ? AND user_id = ?",
            (prize_id, user_id)
        )
        if cursor.fetchone():
            return False  # уже участвует
        
        cursor.execute(
            """INSERT INTO participants 
               (prize_id, user_id, username, first_name, charge_id) 
               VALUES (?, ?, ?, ?, ?)""",
            (prize_id, user_id, username, first_name, charge_id)
        )
        conn.commit()
        return True

def get_participants(prize_id: int):
    """Возвращает всех участников приза."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM participants WHERE prize_id = ?",
            (prize_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

# ---------- РАБОТА С ВЫУЧЕННЫМИ ФРАЗАМИ ----------
def add_learned_phrase(phrase: str):
    """Сохраняет фразу в базу (игнорирует дубликаты)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO learned_phrases (phrase) VALUES (?)",
            (phrase,)
        )
        conn.commit()

def get_random_learned_phrase():
    """Возвращает случайную выученную фразу."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT phrase FROM learned_phrases ORDER BY RANDOM() LIMIT 1")
        row = cursor.fetchone()
        return row["phrase"] if row else None