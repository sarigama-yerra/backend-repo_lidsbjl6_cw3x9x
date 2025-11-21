import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import Product, Order

app = FastAPI(title="E-commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "E-commerce backend is running"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Utility to convert Mongo _id to string

def serialize_doc(doc: dict) -> dict:
    if not doc:
        return doc
    d = {**doc}
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


# Products endpoints

@app.post("/api/products", response_model=dict)
def create_product(product: Product):
    try:
        inserted_id = create_document("product", product)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products", response_model=List[dict])
def list_products(category: Optional[str] = None):
    try:
        filter_dict = {"category": category} if category else {}
        docs = get_documents("product", filter_dict)
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products/seed")
def seed_products():
    """Seed a few demo products if none exist"""
    try:
        existing = get_documents("product", {}, limit=1)
        if existing:
            return {"status": "ok", "message": "Products already exist"}
        demo = [
            Product(title="เสื้อยืดโลโก้", description="ผ้าคอตตอน 100% นุ่มสบาย", price=299.0, category="เสื้อผ้า", in_stock=True, image="https://images.unsplash.com/photo-1520975916090-3105956dac38?w=800&q=80"),
            Product(title="แก้วน้ำสแตนเลส", description="เก็บความเย็นได้นาน 12 ชม.", price=459.0, category="บ้านและไลฟ์สไตล์", in_stock=True, image="https://images.unsplash.com/photo-1610701592028-1a23e5f912c3?w=800&q=80"),
            Product(title="หูฟังไร้สาย", description="แบตอึด เสียงชัด เบสแน่น", price=1290.0, category="อิเล็กทรอนิกส์", in_stock=True, image="https://images.unsplash.com/photo-1518443895914-6bdd97f5d2f1?w=800&q=80"),
        ]
        for p in demo:
            create_document("product", p)
        return {"status": "ok", "message": "Seeded demo products"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Orders endpoints (simple create + list)

@app.post("/api/orders", response_model=dict)
def create_order(order: Order):
    try:
        # naive subtotal validation (sum of items)
        calc_subtotal = sum(item.price * item.quantity for item in order.items)
        if abs(calc_subtotal - order.subtotal) > 0.01:
            raise HTTPException(status_code=400, detail="Subtotal mismatch")
        inserted_id = create_document("order", order)
        return {"id": inserted_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/orders", response_model=List[dict])
def list_orders():
    try:
        docs = get_documents("order")
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Schema endpoint for viewer

@app.get("/schema")
def get_schema():
    from schemas import User, Product, Order
    return {
        "user": User.model_json_schema(),
        "product": Product.model_json_schema(),
        "order": Order.model_json_schema(),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
