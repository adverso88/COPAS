import os
import sys
import logging
import traceback
from fastapi import FastAPI, Request, HTTPException

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear app inmediatamente para garantizar que existe
app = FastAPI(
    title="COPAS CRM API",
    description="CRM de pedidos Shopify con integración WhatsApp",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    servers=[{"url": "/api", "description": "Vercel API"}]
)

# Variable global para capturar errores de inicio
STARTUP_ERROR = None

try:
    # Intentar imports de módulos locales
    # Añadir directorio actual al path por si acaso
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)

    try:
        from .models import ShopifyOrderPayload, OrderStatusUpdate
        from .database import upsert_customer, upsert_order, get_orders, get_order_by_id, update_order_status
        from .whatsapp_service import send_order_confirmation
    except ImportError:
        # Fallback para ejecución local o diferencias de path
        import models
        from models import ShopifyOrderPayload, OrderStatusUpdate
        import database
        from database import upsert_customer, upsert_order, get_orders, get_order_by_id, update_order_status
        import whatsapp_service
        from whatsapp_service import send_order_confirmation

    # SI LLEGA AQUI, LOS IMPORTS FUNCIONARON
    
    # ────────────────────────────────────────────────────
    # ENDPOINTS REALES
    # ────────────────────────────────────────────────────
    @app.post("/webhook/shopify")
    async def receive_shopify_order(payload: ShopifyOrderPayload):
        return {"status": "mock_received", "data": payload.model_dump()}

    @app.get("/orders")
    def list_orders():
        return get_orders(limit=10)

    @app.get("/orders/{order_id}")
    def get_order(order_id: str):
        return get_order_by_id(order_id)

    @app.patch("/orders/{order_id}/status")
    def update_status(order_id: str, body: OrderStatusUpdate):
        return update_order_status(order_id, body.status, body.notes)

except Exception as e:
    # CAPTURAR ERROR CRÍTICO DE INICIO
    STARTUP_ERROR = traceback.format_exc()
    logger.error(f"CRITICAL STARTUP ERROR: {STARTUP_ERROR}")


# ────────────────────────────────────────────────────
# DIAGNOSTICO Y HEALTH CHECK
# ────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    if STARTUP_ERROR:
        return {
            "status": "critical_error", 
            "error": STARTUP_ERROR,
            "python_path": sys.path,
            "cwd": os.getcwd()
        }
    return {"status": "ok", "service": "COPAS CRM API", "database_module": "loaded"}

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    return {
        "detail": "Not Found",
        "path": request.url.path,
        "startup_status": "error" if STARTUP_ERROR else "ok"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("index:app", host="0.0.0.0", port=8000, reload=True)
