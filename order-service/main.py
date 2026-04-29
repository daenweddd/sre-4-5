import os
import logging
import psycopg2
import requests

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order-service")

app = FastAPI(title="Tech Store Order Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_NAME = os.getenv("DB_NAME", "techstore")
DB_USER = os.getenv("DB_USER", "techuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "techpassword")

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8000")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")


class OrderRequest(BaseModel):
    product_id: int
    quantity: int


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def init_db():
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

    conn.commit()
    cursor.close()
    conn.close()


@app.on_event("startup")
def startup():
    init_db()


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
    try:
        conn = get_connection()
        conn.close()
        return {"status": "healthy"}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


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
        cursor.close()
        conn.close()

        logger.info("Order created: %s", order_id)

        return {
            "message": "Order created successfully",
            "order_id": order_id,
            "username": username,
            "product": product["name"],
            "quantity": order.quantity,
            "total_price": total_price
        }

    except Exception as error:
        logger.error("Order error: %s", str(error))
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/orders")
def get_orders():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, product_name, quantity, total_price
            FROM orders;
        """)

        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        orders = []

        for row in rows:
            orders.append({
                "id": row[0],
                "username": row[1],
                "product": row[2],
                "quantity": row[3],
                "total_price": float(row[4])
            })

        return orders

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


Instrumentator().instrument(app).expose(app)