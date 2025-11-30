-- Users table to store customer information
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index on email for fast lookups during login
CREATE INDEX idx_users_email ON users(email);


-- Categories table for organizing products
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- Index on category name for search
CREATE INDEX idx_categories_name ON categories(name);


-- Products table linked to categories
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    category_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE CASCADE
);

-- Index on category_id for filtering products by category
CREATE INDEX idx_products_category_id ON products(category_id);
-- Index on price for range queries
CREATE INDEX idx_products_price ON products(price);


-- Orders table linked to users
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Index on user_id to retrieve order history quickly
CREATE INDEX idx_orders_user_id ON orders(user_id);
-- Index on order_date for reporting
CREATE INDEX idx_orders_order_date ON orders(order_date);


-- Order Items table (Many-to-Many relationship between Orders and Products)
CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
);

-- Index on order_id to get all items for a specific order
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
-- Index on product_id to analyze product sales
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
