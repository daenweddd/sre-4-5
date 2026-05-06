import os
import sys
import logging
import requests

from psycopg2 import pool
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware

required_vars = [
    "DB_HOST",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "PRODUCT_SERVICE_URL",
    "USER_SERVICE_URL",
    "AUTH_SERVICE_URL"
]

missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f"Missing environment variables: {missing}")
    sys.exit(1)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order-service")

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL")


app = FastAPI(title="Tech Store Order Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


try:
    db_pool = pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    if db_pool:
        logger.info("Database connection pool created successfully")

except Exception as error:
    logger.error("Database connection pool creation failed: %s", str(error))
    sys.exit(1)


def get_connection():
    try:
        return db_pool.getconn()
    except Exception as error:
        logger.error("Failed to get database connection: %s", str(error))
        raise


def release_connection(conn):
    if conn:
        db_pool.putconn(conn)


class OrderRequest(BaseModel):
    product_id: int
    quantity: int


def init_db():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100),
                product_id INTEGER,
                product_name VARCHAR(150),
                quantity INTEGER,
                total_price NUMERIC
            );
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_username
            ON orders(username);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_product_id
            ON orders(product_id);
        """)

        conn.commit()
        logger.info("Orders table and indexes initialized successfully")

    except Exception as error:
        logger.error("Database initialization failed: %s", str(error))
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            release_connection(conn)


@app.on_event("startup")
def startup():
    init_db()


def check_service(name, url):
    try:
        response = requests.get(f"{url}/health", timeout=5)

        if response.status_code == 200:
            logger.info("%s is available", name)
            return "available"

        logger.warning("%s returned status code %s", name, response.status_code)
        return "unavailable"

    except Exception as error:
        logger.error("%s is unavailable: %s", name, str(error))
        return "unavailable"


def verify_token(authorization: str):
    try:
        response = requests.get(
            f"{AUTH_SERVICE_URL}/verify",
            headers={"Authorization": authorization},
            timeout=5
        )

        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Unauthorized")

        return response.json()

    except HTTPException:
        raise

    except Exception as error:
        logger.error("Auth service error: %s", str(error))
        raise HTTPException(status_code=503, detail="Auth service unavailable")


def get_product(product_id: int):
    try:
        response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            timeout=5
        )

        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Product not found")

        return response.json()

    except HTTPException:
        raise

    except Exception as error:
        logger.error("Product service error: %s", str(error))
        raise HTTPException(status_code=503, detail="Product service unavailable")


@app.get("/")
def home():
    return {
        "service": "order-service",
        "status": "running"
    }


@app.get("/health")
def health():
    conn = None

    try:
        conn = get_connection()

        dependencies = {
            "product_service": check_service("product-service", PRODUCT_SERVICE_URL),
            "user_service": check_service("user-service", USER_SERVICE_URL),
            "auth_service": check_service("auth-service", AUTH_SERVICE_URL)
        }

        return {
            "status": "healthy",
            "database": "connected",
            "dependencies": dependencies
        }

    except Exception as error:
        logger.error("Health check failed: %s", str(error))
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(error)}"
        )

    finally:
        if conn:
            release_connection(conn)


@app.post("/orders")
def create_order(order: OrderRequest, authorization: str = Header(None)):
    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing token")

    user_data = verify_token(authorization)
    username = user_data["username"]

    product = get_product(order.product_id)

    if order.quantity <= 0:
        raise HTTPException(status_code=400, detail="Invalid quantity")

    if order.quantity > product["stock"]:
        raise HTTPException(status_code=400, detail="Not enough stock")

    total_price = product["price"] * order.quantity

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO orders (username, product_id, product_name, quantity, total_price)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                username,
                product["id"],
                product["name"],
                order.quantity,
                total_price
            )
        )

        order_id = cursor.fetchone()[0]

        conn.commit()

        logger.info("Order created successfully: %s", order_id)

        return {
            "message": "Order created successfully",
            "order_id": order_id,
            "username": username,
            "product": product["name"],
            "quantity": order.quantity,
            "total_price": total_price
        }

    except Exception as error:
        if conn:
            conn.rollback()

        logger.error("Order creation failed: %s", str(error))
        raise HTTPException(status_code=500, detail=str(error))

    finally:
        if cursor:
            cursor.close()
        if conn:
            release_connection(conn)


@app.get("/orders")
def get_orders():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, product_name, quantity, total_price
            FROM orders
            ORDER BY id;
        """)

        rows = cursor.fetchall()

        orders = []

        for row in rows:
            orders.append({
                "id": row[0],
                "username": row[1],
                "product": row[2],
                "quantity": row[3],
                "total_price": float(row[4])
            })

        logger.info("Orders retrieved successfully")

        return orders

    except Exception as error:
        logger.error("Failed to retrieve orders: %s", str(error))
        raise HTTPException(status_code=500, detail=str(error))

    finally:
        if cursor:
            cursor.close()
        if conn:
            release_connection(conn)



Instrumentator().instrument(app).expose(app)