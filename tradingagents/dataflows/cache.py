"""SQLite 缓存模块

缓存位置: ~/.my_qmt/cache/stock_data.db
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

# ============================================================
# 缓存配置
# ============================================================

CACHE_DIR = Path.home() / ".my_qmt" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = CACHE_DIR / "stock_data.db"

# 缓存有效期
DAILY_KLINE_EXPIRY_HOURS = 24  # 历史K线: 24小时
INDEX_EXPIRY_DAYS = 7          # 指数成分股: 7天


# ============================================================
# 数据库初始化
# ============================================================

def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")  # 提高并发性能
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_connection()
    cursor = conn.cursor()

    # 历史K线数据
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_kline (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            close REAL,
            high REAL,
            low REAL,
            volume INTEGER,
            amount REAL,
            amplitude REAL,
            change_pct REAL,
            change REAL,
            turnover REAL,
            real_turnover REAL,
            float_shares REAL,
            total_shares REAL,
            market_cap REAL,
            float_cap REAL,
            PRIMARY KEY (symbol, date)
        )
    """)

    # 指数成分股
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS index_constituents (
            index_code TEXT NOT NULL,
            stock_code TEXT NOT NULL,
            stock_name TEXT,
            weight REAL,
            update_date TEXT,
            PRIMARY KEY (index_code, stock_code)
        )
    """)

    # 缓存元数据
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_meta (
            key TEXT PRIMARY KEY,
            last_update TEXT,
            row_count INTEGER
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kline_symbol ON daily_kline(symbol)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kline_date ON daily_kline(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_index_code ON index_constituents(index_code)")

    # 数据库迁移: 添加新字段 (如果不存在)
    new_columns = [
        ("real_turnover", "REAL"),
        ("float_shares", "REAL"),
        ("total_shares", "REAL"),
        ("market_cap", "REAL"),
        ("float_cap", "REAL"),
    ]
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE daily_kline ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass  # 字段已存在

    conn.commit()
    conn.close()


# 初始化数据库
init_db()


# ============================================================
# 历史K线缓存
# ============================================================

def get_cached_kline(symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """从缓存获取历史K线数据

    Args:
        symbol: 股票代码
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        DataFrame or None (缓存未命中)
    """
    # 检查缓存是否有效
    cache_key = f"daily_kline_{symbol}"
    if not is_cache_valid(cache_key, DAILY_KLINE_EXPIRY_HOURS):
        return None

    conn = get_connection()
    try:
        query = """
            SELECT date, open, close, high, low, volume, amount,
                   amplitude, change_pct, change, turnover, real_turnover,
                   float_shares, total_shares, market_cap, float_cap
            FROM daily_kline
            WHERE symbol = ? AND date >= ? AND date <= ?
            ORDER BY date
        """
        df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))

        if df.empty:
            return None

        # 设置日期索引
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        df.index.name = "Date"

        # 重命名列
        df = df.rename(columns={
            "open": "Open",
            "close": "Close",
            "high": "High",
            "low": "Low",
            "volume": "Volume",
            "amount": "Amount",
            "amplitude": "Amplitude",
            "change_pct": "Change_Pct",
            "change": "Change",
            "turnover": "Turnover",
            "real_turnover": "Real_Turnover",
            "float_shares": "Float_Shares",
            "total_shares": "Total_Shares",
            "market_cap": "Market_Cap",
            "float_cap": "Float_Cap",
        })

        return df

    except Exception:
        return None
    finally:
        conn.close()


def save_kline_to_cache(symbol: str, df: pd.DataFrame):
    """保存历史K线数据到缓存

    Args:
        symbol: 股票代码
        df: DataFrame with OHLCV data
    """
    if df.empty:
        return

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 准备数据
        records = []
        for date, row in df.iterrows():
            date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)
            records.append((
                symbol,
                date_str,
                row.get("Open"),
                row.get("Close"),
                row.get("High"),
                row.get("Low"),
                int(row.get("Volume", 0)) if pd.notna(row.get("Volume")) else None,
                row.get("Amount"),
                row.get("Amplitude"),
                row.get("Change_Pct"),
                row.get("Change"),
                row.get("Turnover"),
                row.get("Real_Turnover"),
                row.get("Float_Shares"),
                row.get("Total_Shares"),
                row.get("Market_Cap"),
                row.get("Float_Cap"),
            ))

        # 批量插入 (使用 REPLACE 实现 upsert)
        cursor.executemany("""
            REPLACE INTO daily_kline
            (symbol, date, open, close, high, low, volume, amount,
             amplitude, change_pct, change, turnover, real_turnover,
             float_shares, total_shares, market_cap, float_cap)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        # 更新元数据
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            REPLACE INTO cache_meta (key, last_update, row_count)
            VALUES (?, ?, ?)
        """, (f"daily_kline_{symbol}", now, len(records)))

        conn.commit()

    except Exception as e:
        conn.rollback()
    finally:
        conn.close()


def get_kline_missing_dates(symbol: str, start_date: str, end_date: str) -> list[tuple[str, str]]:
    """获取缓存中缺失的日期范围

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        list of (start, end) tuples representing missing ranges
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 获取缓存中的日期
        cursor.execute("""
            SELECT DISTINCT date FROM daily_kline
            WHERE symbol = ? AND date >= ? AND date <= ?
            ORDER BY date
        """, (symbol, start_date, end_date))

        cached_dates = {row[0] for row in cursor.fetchall()}

        if not cached_dates:
            return [(start_date, end_date)]

        # 计算缺失日期
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        missing_ranges = []
        current = start_dt
        range_start = None

        while current <= end_dt:
            date_str = current.strftime("%Y-%m-%d")
            if date_str not in cached_dates:
                if range_start is None:
                    range_start = date_str
            else:
                if range_start is not None:
                    missing_ranges.append((range_start, (current - timedelta(days=1)).strftime("%Y-%m-%d")))
                    range_start = None
            current += timedelta(days=1)

        if range_start is not None:
            missing_ranges.append((range_start, end_date))

        return missing_ranges

    except Exception:
        return [(start_date, end_date)]
    finally:
        conn.close()


# ============================================================
# 指数成分股缓存
# ============================================================

def get_cached_index_stocks(index_code: str) -> Optional[list[dict]]:
    """从缓存获取指数成分股

    Args:
        index_code: 指数代码

    Returns:
        list[dict] or None (缓存未命中)
    """
    cache_key = f"index_{index_code}"
    if not is_cache_valid(cache_key, INDEX_EXPIRY_DAYS * 24):
        return None

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT stock_code, stock_name, weight
            FROM index_constituents
            WHERE index_code = ?
            ORDER BY weight DESC
        """, (index_code,))

        results = []
        for row in cursor.fetchall():
            results.append({
                "code": row[0],
                "name": row[1],
                "weight": row[2],
            })

        return results if results else None

    except Exception:
        return None
    finally:
        conn.close()


def save_index_stocks_to_cache(index_code: str, stocks: list[dict]):
    """保存指数成分股到缓存

    Args:
        index_code: 指数代码
        stocks: list[dict] with code, name, weight
    """
    if not stocks:
        return

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 先删除旧数据
        cursor.execute("DELETE FROM index_constituents WHERE index_code = ?", (index_code,))

        # 插入新数据
        today = datetime.now().strftime("%Y-%m-%d")
        records = [
            (index_code, s["code"], s["name"], s.get("weight", 0), today)
            for s in stocks
        ]

        cursor.executemany("""
            INSERT INTO index_constituents (index_code, stock_code, stock_name, weight, update_date)
            VALUES (?, ?, ?, ?, ?)
        """, records)

        # 更新元数据
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            REPLACE INTO cache_meta (key, last_update, row_count)
            VALUES (?, ?, ?)
        """, (f"index_{index_code}", now, len(records)))

        conn.commit()

    except Exception as e:
        conn.rollback()
    finally:
        conn.close()


# ============================================================
# 缓存管理
# ============================================================

def is_cache_valid(key: str, expiry_hours: int) -> bool:
    """检查缓存是否有效

    Args:
        key: 缓存键
        expiry_hours: 有效期 (小时)

    Returns:
        bool
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT last_update FROM cache_meta WHERE key = ?", (key,))
        row = cursor.fetchone()

        if row is None:
            return False

        last_update = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - last_update).total_seconds() < expiry_hours * 3600

    except Exception:
        return False
    finally:
        conn.close()


def cache_stats() -> dict:
    """获取缓存统计信息

    Returns:
        dict with cache statistics
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # K线数据统计
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM daily_kline")
        kline_symbols = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM daily_kline")
        kline_rows = cursor.fetchone()[0]

        # 指数成分股统计
        cursor.execute("SELECT COUNT(DISTINCT index_code) FROM index_constituents")
        index_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM index_constituents")
        index_rows = cursor.fetchone()[0]

        # 数据库文件大小
        db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0

        return {
            "db_path": str(DB_PATH),
            "db_size_mb": round(db_size / 1024 / 1024, 2),
            "kline_symbols": kline_symbols,
            "kline_rows": kline_rows,
            "index_count": index_count,
            "index_rows": index_rows,
        }

    except Exception:
        return {"error": "Failed to get cache stats"}
    finally:
        conn.close()


def cache_clear(pattern: str = None):
    """清除缓存

    Args:
        pattern: 清除模式
            - None: 清除所有缓存
            - "kline": 只清除K线数据
            - "index": 只清除指数成分股
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if pattern is None:
            cursor.execute("DELETE FROM daily_kline")
            cursor.execute("DELETE FROM index_constituents")
            cursor.execute("DELETE FROM cache_meta")
        elif pattern == "kline":
            cursor.execute("DELETE FROM daily_kline")
            cursor.execute("DELETE FROM cache_meta WHERE key LIKE 'daily_kline_%'")
        elif pattern == "index":
            cursor.execute("DELETE FROM index_constituents")
            cursor.execute("DELETE FROM cache_meta WHERE key LIKE 'index_%'")

        conn.commit()

    except Exception:
        conn.rollback()
    finally:
        conn.close()


def cache_clear_expired():
    """清除过期缓存"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 清除过期的K线缓存
        kline_expiry = (datetime.now() - timedelta(hours=DAILY_KLINE_EXPIRY_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            DELETE FROM cache_meta
            WHERE key LIKE 'daily_kline_%' AND last_update < ?
        """, (kline_expiry,))

        # 清除过期的指数缓存
        index_expiry = (datetime.now() - timedelta(days=INDEX_EXPIRY_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            DELETE FROM cache_meta
            WHERE key LIKE 'index_%' AND last_update < ?
        """, (index_expiry,))

        conn.commit()

    except Exception:
        conn.rollback()
    finally:
        conn.close()
