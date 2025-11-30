import psycopg2 
import random
import time
import os
import io
import csv
import string
from datetime import datetime, timedelta

# Configuration
NUM_ROWS = 1_000_000
BATCH_SIZE = 10000  # Not used for COPY, but good for reference

# Database Connection Parameters
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Please ensure you have a PostgreSQL database running and credentials are correct.")
        print("You can set DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT environment variables.")
        exit(1)

def generate_random_string(length=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def bulk_insert(cursor, table_name, columns, data_generator):
    print(f"Preparing data for {table_name}...")
    
    # Use StringIO as an in-memory file
    f = io.StringIO()
    writer = csv.writer(f)
    
    # Generate all data and write to the in-memory file
    # For 1M rows, this might take ~100-200MB RAM, which is acceptable
    count = 0
    for row in data_generator():
        writer.writerow(row)
        count += 1
        if count % 100000 == 0:
            print(f"  Generated {count} rows...", end='\r')
    
    print(f"  Generated {count} rows. Inserting into DB...")
    f.seek(0)
    
    cols_str = ', '.join(columns)
    sql = f"COPY {table_name} ({cols_str}) FROM STDIN WITH (FORMAT CSV)"
    
    try:
        cursor.copy_expert(sql, f)
        print(f"Successfully inserted {count} rows into {table_name}.")
    except Exception as e:
        print(f"Error inserting into {table_name}: {e}")
        raise

# Data Generators
def generate_users_data():
    for i in range(1, NUM_ROWS + 1):
        user_id = i
        username = f"user_{i}"
        email = f"user_{i}@example.com"
        password_hash = generate_random_string(32)
        created_at = datetime.now().isoformat()
        yield [user_id, username, email, password_hash, created_at]

def generate_categories_data():
    for i in range(1, NUM_ROWS + 1):
        category_id = i
        name = f"Category {i}"
        description = f"Description for category {i}"
        yield [category_id, name, description]

def generate_products_data():
    for i in range(1, NUM_ROWS + 1):
        product_id = i
        category_id = random.randint(1, NUM_ROWS)
        name = f"Product {i}"
        description = f"Description for product {i}"
        price = round(random.uniform(10.0, 1000.0), 2)
        stock_quantity = random.randint(0, 1000)
        created_at = datetime.now().isoformat()
        yield [product_id, category_id, name, description, price, stock_quantity, created_at]

def generate_orders_data():
    statuses = ['pending', 'completed', 'shipped', 'cancelled']
    for i in range(1, NUM_ROWS + 1):
        order_id = i
        user_id = random.randint(1, NUM_ROWS)
        order_date = (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
        status = random.choice(statuses)
        total_amount = round(random.uniform(20.0, 2000.0), 2)
        yield [order_id, user_id, order_date, status, total_amount]

def generate_order_items_data():
    for i in range(1, NUM_ROWS + 1):
        order_item_id = i
        order_id = random.randint(1, NUM_ROWS)
        product_id = random.randint(1, NUM_ROWS)
        quantity = random.randint(1, 5)
        unit_price = round(random.uniform(10.0, 1000.0), 2)
        yield [order_item_id, order_id, product_id, quantity, unit_price]

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    
    start_time = time.time()
    
    try:
        # Optional: Truncate tables to avoid PK conflicts if running multiple times
        # Be careful with this in production!
        print("Truncating tables...")
        cur.execute("TRUNCATE TABLE order_items, orders, products, categories, users RESTART IDENTITY CASCADE;")
        
        bulk_insert(cur, 'users', ['user_id', 'username', 'email', 'password_hash', 'created_at'], generate_users_data)
        bulk_insert(cur, 'categories', ['category_id', 'name', 'description'], generate_categories_data)
        bulk_insert(cur, 'products', ['product_id', 'category_id', 'name', 'description', 'price', 'stock_quantity', 'created_at'], generate_products_data)
        bulk_insert(cur, 'orders', ['order_id', 'user_id', 'order_date', 'status', 'total_amount'], generate_orders_data)
        bulk_insert(cur, 'order_items', ['order_item_id', 'order_id', 'product_id', 'quantity', 'unit_price'], generate_order_items_data)
        
        conn.commit()
        print(f"All data generated and inserted successfully. Total time: {time.time() - start_time:.2f} seconds.")
        
    except Exception as e:
        conn.rollback()
        print(f"An error occurred: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
