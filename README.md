# E-Commerce Data Engineering Project

A high-performance data engineering project featuring a PostgreSQL database with 5 million records, automated data generation, and a FastAPI REST API with automatic master/slave failover capabilities.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Database Schema](#database-schema)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Project Structure](#project-structure)

## 🎯 Overview

This project demonstrates a complete data engineering solution for an e-commerce platform, including:
- A normalized relational database schema with 5 tables
- Automated generation of 1 million records per table (5M total)
- RESTful API with automatic database failover
- High-performance bulk data insertion using PostgreSQL COPY

## ✨ Features

### Database
- **5 Normalized Tables**: Users, Categories, Products, Orders, Order Items
- **Primary & Foreign Keys**: Proper relational integrity
- **Optimized Indexes**: Strategic indexing for common query patterns
- **1M Rows Per Table**: Realistic dataset for testing and development

### API with Automatic Failover
- **Master/Slave Architecture**: Reads from slave by default
- **Automatic Failover**: Switches to master when slave is down
- **Auto-Recovery**: Switches back to slave when available
- **7 REST Endpoints**: Row counts, aggregations, top-N queries, joins, filters, search

## 🗄️ Database Schema

### Tables

1. **users** - Customer information
   - Primary Key: `user_id`
   - Indexed: `email`

2. **categories** - Product categories
   - Primary Key: `category_id`
   - Indexed: `name`

3. **products** - Product catalog
   - Primary Key: `product_id`
   - Foreign Key: `category_id` → `categories`
   - Indexed: `category_id`, `price`

4. **orders** - Customer orders
   - Primary Key: `order_id`
   - Foreign Key: `user_id` → `users`
   - Indexed: `user_id`, `order_date`

5. **order_items** - Order line items (many-to-many)
   - Primary Key: `order_item_id`
   - Foreign Keys: `order_id` → `orders`, `product_id` → `products`
   - Indexed: `order_id`, `product_id`

## 📦 Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/grgpk/comm-school-data-engineering.git
cd comm-school-data-engineering
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install psycopg2-binary fastapi uvicorn
```

### 4. Set Up Database

```bash
# Create PostgreSQL database
createdb your_database_name

# Or using psql
psql -U postgres
CREATE DATABASE your_database_name;
\q
```

### 5. Create Tables

```bash
psql -U postgres -d your_database_name -f tables.sql
```

## 💻 Usage

### Generate Test Data

Generate 1 million records for each table:

```bash
# Set database credentials (optional, defaults to localhost)
export DB_HOST=localhost
export DB_NAME=your_database_name
export DB_USER=postgres
export DB_PASS=your_password

# Run data generation
python generate_data.py
```

**Expected runtime**: ~2-5 minutes depending on hardware.

### Start the API

```bash
# Configure master/slave hosts (optional)
export MASTER_DB_HOST=localhost
export SLAVE_DB_HOST=localhost  # For testing, use same host

# Start the API server
uvicorn api:app --reload
```

The API will be available at:
- **Base URL**: http://127.0.0.1:8000
- **Interactive Docs**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## 🔌 API Endpoints

### Health & Status
- `GET /` - API status and slave health

### Analytics
- `GET /stats/counts` - Row counts for all tables
- `GET /products/stats` - Product price statistics (AVG, MIN, MAX)
- `GET /categories/revenue` - Top 10 categories by revenue

### Queries
- `GET /products/top?limit=5` - Top N most expensive products (with joins)
- `GET /users/{user_id}/orders` - Order history for a user
- `GET /orders/status/{status}?limit=10` - Orders filtered by status
- `GET /products/search?q=keyword` - Search products by name

### Example Request

```bash
# Get row counts
curl http://127.0.0.1:8000/stats/counts

# Get top 10 products
curl http://127.0.0.1:8000/products/top?limit=10

# Search products
curl http://127.0.0.1:8000/products/search?q=Product
```

## ⚙️ Configuration

### Environment Variables

#### Database Connection
```bash
DB_HOST=localhost          # Database host
DB_NAME=postgres           # Database name
DB_USER=postgres           # Database user
DB_PASS=postgres           # Database password
DB_PORT=5432               # Database port
```

#### Failover Configuration
```bash
MASTER_DB_HOST=localhost   # Master database host
SLAVE_DB_HOST=localhost    # Slave database host (read replica)
```

### Failover Behavior

The API automatically:
1. **Tries Slave First**: All read queries go to the slave by default
2. **Detects Failure**: If slave connection fails, logs error and switches to master
3. **Periodic Health Checks**: Checks slave every 10 seconds
4. **Auto-Recovery**: Switches back to slave once it's healthy

## 📁 Project Structure

```
data-engineering/
├── api.py              # FastAPI application with failover logic
├── generate_data.py    # Bulk data generation script
├── tables.sql          # Database schema definition
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## 🛠️ Technical Details

### Data Generation
- Uses PostgreSQL's `COPY` command for high-speed bulk inserts
- Generates data in-memory using Python generators
- ~100-200MB RAM usage for 1M rows
- Automatic transaction management with rollback on error

### API Performance
- Connection pooling via dependency injection
- `RealDictCursor` for easy JSON serialization
- Automatic connection cleanup using `yield` pattern
- Logging for monitoring failover events

## 📝 License

This project is part of the Comm School Data Engineering curriculum.

## 👨‍💻 Author

**grgpk** - [GitHub Profile](https://github.com/grgpk)

---

**Note**: This is a demonstration project for educational purposes. For production use, consider additional features like connection pooling, caching, authentication, and more sophisticated failover strategies.
