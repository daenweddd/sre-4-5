import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product-service")

app = FastAPI(title="Tech Store Product Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

products = [
    {
        "id": 1,
        "name": "MacBook Pro 14",
        "category": "Laptop",
        "brand": "Apple",
        "price": 1999,
        "stock": 10
    },
    {
        "id": 2,
        "name": "iPhone 15",
        "category": "Smartphone",
        "brand": "Apple",
        "price": 999,
        "stock": 20
    },
    {
        "id": 3,
        "name": "Samsung Galaxy S24",
        "category": "Smartphone",
        "brand": "Samsung",
        "price": 899,
        "stock": 15
    },
    {
        "id": 4,
        "name": "Sony WH-1000XM5",
        "category": "Headphones",
        "brand": "Sony",
        "price": 399,
        "stock": 25
    }
]


class ProductRequest(BaseModel):
    name: str
    category: str
    brand: str
    price: float
    stock: int


@app.get("/")
def home():
    return {
        "service": "product-service",
        "status": "running"
    }


@app.get("/products")
def get_products():
    logger.info("Product list requested")
    return products


@app.get("/products/{product_id}")
def get_product(product_id: int):
    for product in products:
        if product["id"] == product_id:
            logger.info("Product found: %s", product["name"])
            return product

    logger.error("Product not found: id=%s", product_id)
    raise HTTPException(status_code=404, detail="Product not found")


@app.post("/products")
def create_product(product: ProductRequest):
    new_product = {
        "id": len(products) + 1,
        "name": product.name,
        "category": product.category,
        "brand": product.brand,
        "price": product.price,
        "stock": product.stock
    }

    products.append(new_product)

    logger.info("New product added: %s", product.name)

    return {
        "message": "Product added successfully",
        "product": new_product
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


Instrumentator().instrument(app).expose(app)