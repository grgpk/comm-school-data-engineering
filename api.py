import time
import os
import logging
from typing import List

from fastapi import FastAPI, Depends
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime


# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Failover API", description="API with automatic Master/Slave failover")

# Database Configuration
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
DB_MASTER_PORT = os.environ.get("DB_MASTER_PORT", "5432")
DB_SLAVE_PORT = os.environ.get("DB_SLAVE_PORT", "5433")

# Master DB Config
MASTER_HOST = os.environ.get("MASTER_DB_HOST", "localhost")

# Slave DB Config (Default to localhost for testing if not set, but logic treats it as separate)
SLAVE_HOST = os.environ.get("SLAVE_DB_HOST", "localhost")

class DatabaseManager:
    def __init__(self):
        self.master_params = {
            "host": MASTER_HOST, "database": DB_NAME, "user": DB_USER, "password": DB_PASS, "port": DB_MASTER_PORT
        }
        self.slave_params = {
            "host": SLAVE_HOST, "database": DB_NAME, "user": DB_USER, "password": DB_PASS, "port": DB_SLAVE_PORT
        }
        self.slave_is_down = False
        self.last_slave_check = 0
        self.retry_interval = 10  # Seconds to wait before retrying slave

    def _connect(self, params, desc):
        try:
            conn = psycopg2.connect(**params)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to {desc}: {e}")
            raise

    def check_slave_health(self):
        """Try to connect to slave to see if it's back up."""
        try:
            conn = self._connect(self.slave_params, "Slave Probe")
            conn.close()
            logger.info("Slave is back ONLINE.")
            return True
        except:
            return False

    def get_connection(self):
        """
        Returns a database connection.
        Logic:
        1. If Slave is UP, try Slave.
           - If success, return Slave conn.
           - If fail, mark Slave DOWN, log, return Master conn.
        2. If Slave is DOWN:
           - Check if retry interval passed.
             - If yes, probe Slave. If success, mark UP, return Slave conn.
           - Return Master conn.
        """
        current_time = time.time()

        # If slave is marked down, check if we should retry
        if self.slave_is_down:
            if current_time - self.last_slave_check > self.retry_interval:
                logger.info("Retrying Slave connection...")
                if self.check_slave_health():
                    self.slave_is_down = False
                    self.last_slave_check = current_time
                else:
                    self.last_slave_check = current_time
                    logger.info("Slave is still DOWN. Using Master.")
                    return self._connect(self.master_params, "Master")
            else:
                # Retry interval hasn't passed, stick to Master
                return self._connect(self.master_params, "Master")

        # Try connecting to Slave
        try:
            conn = self._connect(self.slave_params, "Slave")
            # logger.info("Connected to Slave.") # Verbose
            return conn
        except Exception:
            logger.warning("Slave connection failed! Switching to Master.")
            self.slave_is_down = True
            self.last_slave_check = current_time
            return self._connect(self.master_params, "Master")

db_manager = DatabaseManager()

def get_db():
    conn = db_manager.get_connection()
    try:
        yield conn
    finally:
        conn.close()

# --- Pydantic Models for Responses ---
class TableCounts(BaseModel):
    users: int
    products: int
    orders: int

class ProductStats(BaseModel):
    avg_price: float
    min_price: float
    max_price: float

class Product(BaseModel):
    product_id: int
    name: str
    price: float
    category_name: str

class UserOrder(BaseModel):
    order_id: int
    order_date: datetime
    total_amount: float
    status: str


# --- Endpoints ---

@app.get("/")
def root():
    return {"message": "Failover API is running", "slave_status": "DOWN" if db_manager.slave_is_down else "UP"}

# 1. Row Counts
@app.get("/stats/counts")
def get_row_counts(db=Depends(get_db)):
    cursor = db.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT count(*) as c FROM users")
        users = cursor.fetchone()['c']
        cursor.execute("SELECT count(*) as c FROM products")
        products = cursor.fetchone()['c']
        cursor.execute("SELECT count(*) as c FROM orders")
        orders = cursor.fetchone()['c']
        return {"users": users, "products": products, "orders": orders}
    finally:
        cursor.close()

# 2. Aggregations (AVG, MIN, MAX)
@app.get("/products/stats", response_model=ProductStats)
def get_product_stats(db=Depends(get_db)):
    cursor = db.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT 
                AVG(price) as avg_price, 
                MIN(price) as min_price, 
                MAX(price) as max_price 
            FROM products
        """)
        result = cursor.fetchone()
        return result
    finally:
        cursor.close()

# 3. Top-N Results
@app.get("/products/top", response_model=List[Product])
def get_top_products(limit: int = 5, db=Depends(get_db)):
    cursor = db.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT p.product_id, p.name, p.price, c.name as category_name
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            ORDER BY p.price DESC
            LIMIT %s
        """, (limit,))
        results = cursor.fetchall()
        return results
    finally:
        cursor.close()

# 4. Joins & Filtered Queries (User Orders)
@app.get("/users/{user_id}/orders")
def get_user_orders(user_id: int, db=Depends(get_db)):
    cursor = db.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT o.order_id, o.order_date, o.total_amount, o.status
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE u.user_id = %s
            ORDER BY o.order_date DESC
            LIMIT 10
        """, (user_id,))
        results = cursor.fetchall()
        return results
    finally:
        cursor.close()

# 5. Complex Aggregation (Revenue per Category) - it is slow
@app.get("/categories/revenue")
def get_category_revenue(db=Depends(get_db)):
    cursor = db.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT c.name as category, SUM(oi.quantity * oi.unit_price) as total_revenue
            FROM categories c
            JOIN products p ON c.category_id = p.category_id
            JOIN order_items oi ON p.product_id = oi.product_id
            GROUP BY c.name
            ORDER BY total_revenue DESC
            LIMIT 10
        """)
        results = cursor.fetchall()
        return results
    finally:
        cursor.close()

# 6. Filtered Query (Orders by Status)
@app.get("/orders/status/{status}")
def get_orders_by_status(status: str, limit: int = 10, db=Depends(get_db)):
    cursor = db.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT order_id, user_id, total_amount, order_date
            FROM orders
            WHERE status = %s
            LIMIT %s
        """, (status, limit))
        results = cursor.fetchall()
        return results
    finally:
        cursor.close()

# 7. Search
@app.get("/products/search")
def search_products(q: str, db=Depends(get_db)):
    cursor = db.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT product_id, name, price, description
            FROM products
            WHERE name ILIKE %s
            LIMIT 10
        """, (f"%{q}%",))
        results = cursor.fetchall()
        return results
    finally:
        cursor.close()
