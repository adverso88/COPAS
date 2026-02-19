"""
main.py — API Backend FastAPI para CRM de Pedidos Shopify + WhatsApp

Endpoints:
  POST /webhook/shopify      — Recibe pedidos desde Make (Integromat)
  GET  /orders               — Lista pedidos del CRM
  GET  /orders/{id}          — Detalle de un pedido
  PATCH /orders/{id}/status  — Actualiza estado del pedido
  POST /orders/{id}/resend-whatsapp — Reenvía WhatsApp manualmente
  GET  /stats                — Estadísticas del dashboard
  GET  /health               — Health check
"""
import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Header, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Optional, List

# Forzar el directorio api/ en el path
sys.path.append(os.path.dirname(__file__))

try:
    from .models import ShopifyOrderPayload, OrderStatusUpdate
    from .database import upsert_customer, upsert_order, get_orders, get_order_by_id, update_order_status, mark_whatsapp_sent, get_dashboard_stats
    from .whatsapp_service import send_order_confirmation
except (ImportError, ValueError):
    import models
    from models import ShopifyOrderPayload, OrderStatusUpdate
    import database
    from database import upsert_customer, upsert_order, get_orders, get_order_by_id, update_order_status, mark_whatsapp_sent, get_dashboard_stats
    import whatsapp_service
    from whatsapp_service import send_order_confirmation

load_dotenv()

# ────────────────────────────────────────────────────
# Configuración
# ────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET_TOKEN", "")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app = FastAPI(
    title="COPAS CRM API",
    description="CRM de pedidos Shopify con integración WhatsApp",
    version="1.0.0",
)

# Middleware para depurar rutas en Vercel
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"🚀 Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"🏁 Response status: {response.status_code}")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────────────────────────────────
# Seguridad: verificar token del webhook
# ────────────────────────────────────────────────────
def verify_webhook_token(x_webhook_token: Optional[str] = Header(None)):
    """
    Valida el token secreto que Make envía en el header X-Webhook-Token.
    Si WEBHOOK_SECRET_TOKEN no está configurado, omite la validación (modo dev).
    """
    if WEBHOOK_SECRET and x_webhook_token != WEBHOOK_SECRET:
        logger.warning(f"Token inválido recibido: {x_webhook_token}")
        raise HTTPException(status_code=401, detail="Token de webhook inválido")
    return True


# ────────────────────────────────────────────────────
# ENDPOINTS
# ────────────────────────────────────────────────────

@app.get("/")
async def root_diagnostic(request: Request):
    return {
        "status": "online",
        "message": "COPAS API is running",
        "path_received": request.url.path,
        "hint": "Si ves esto, las rutas deben configurarse sin el prefijo /api en el decorador"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "COPAS CRM API"}

@app.post("/webhook/shopify", dependencies=[Depends(verify_webhook_token)])
async def receive_shopify_order(payload: ShopifyOrderPayload):
    """
    Recibe un pedido de Shopify vía Make.
    
    Flujo:
    1. Extraer datos del cliente
    2. Upsert cliente en Supabase
    3. Upsert pedido (idempotente por shopify_order_id)
    4. Enviar WhatsApp de confirmación si hay teléfono
    5. Retornar confirmación a Make
    """
    logger.info(f"📦 Pedido recibido: {payload.order_number} (Shopify ID: {payload.shopify_order_id})")

    # 1. Extraer datos del cliente
    customer = payload.customer or {}
    shipping = payload.shipping_address

    # Nombre del cliente
    first_name = getattr(customer, "first_name", None) or ""
    last_name = getattr(customer, "last_name", None) or ""
    customer_name = f"{first_name} {last_name}".strip() or "Cliente"

    # Email
    customer_email = getattr(customer, "email", None)

    # Teléfono: intentar customer.phone primero, luego shipping_address.phone
    customer_phone = getattr(customer, "phone", None)
    if not customer_phone and shipping:
        customer_phone = getattr(shipping, "phone", None)

    # 2. Upsert cliente
    customer_record = upsert_customer({
        "name": customer_name,
        "email": customer_email,
        "phone": customer_phone,
    })
    customer_id = customer_record.get("id")

    # 3. Preparar datos del pedido
    line_items_data = [item.model_dump() for item in payload.line_items]
    shipping_data = shipping.model_dump() if shipping else {}

    order_data = {
        "shopify_order_id": payload.shopify_order_id,
        "order_number": payload.order_number,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "shipping_address": shipping_data,
        "line_items": line_items_data,
        "total_price": payload.total_price,
        "currency": payload.currency,
        "financial_status": payload.financial_status,
        "fulfillment_status": payload.fulfillment_status,
        "status": "nuevo",
        "notes": payload.note,
        "tags": payload.tags,
        "whatsapp_sent": False,
    }

    # 4. Upsert pedido (idempotente)
    order_record, is_new = upsert_order(order_data)
    order_id = order_record.get("id")

    if not is_new:
        logger.info(f"⚠️ Pedido {payload.shopify_order_id} ya existía. No se duplica.")
        return {
            "success": True,
            "order_id": order_id,
            "message": "Pedido ya existente, sin cambios",
            "whatsapp_sent": False,
        }

    # 5. Enviar WhatsApp si hay teléfono
    whatsapp_result = {"success": False, "message_id": None, "error": "Sin teléfono"}

    if customer_phone:
        logger.info(f"📱 Enviando WhatsApp a {customer_phone}...")
        whatsapp_result = send_order_confirmation(
            phone=customer_phone,
            customer_name=customer_name,
            order_number=payload.order_number,
            total=payload.total_price,
            currency=payload.currency,
        )
        if whatsapp_result["success"]:
            logger.info(f"✅ WhatsApp enviado. Message ID: {whatsapp_result['message_id']}")
        else:
            logger.warning(f"❌ WhatsApp falló: {whatsapp_result['error']}")
    else:
        logger.warning(f"⚠️ Pedido {payload.order_number} sin teléfono — WhatsApp omitido")

    # Registrar resultado del WhatsApp
    if order_id:
        mark_whatsapp_sent(
            order_id=order_id,
            success=whatsapp_result["success"],
            message_id=whatsapp_result.get("message_id"),
            error=whatsapp_result.get("error"),
        )

    return {
        "success": True,
        "order_id": order_id,
        "order_number": payload.order_number,
        "whatsapp_sent": whatsapp_result["success"],
        "whatsapp_error": whatsapp_result.get("error") if not whatsapp_result["success"] else None,
    }


@app.get("/orders")
def list_orders(
    status: Optional[str] = Query(None),
    whatsapp_sent: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Lista pedidos del CRM con filtros opcionales."""
    orders = get_orders(status=status, whatsapp_sent=whatsapp_sent, limit=limit, offset=offset)
    return {"orders": orders, "count": len(orders)}


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    """Detalle completo de un pedido con historial de WhatsApp."""
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return order


@app.patch("/orders/{order_id}/status")
def update_status(order_id: str, body: OrderStatusUpdate):
    """Actualiza el estado de un pedido desde el CRM."""
    valid_statuses = ["nuevo", "en_proceso", "enviado", "completado", "cancelado"]
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Usa: {', '.join(valid_statuses)}",
        )
    updated = update_order_status(order_id, body.status, body.notes)
    if not updated:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return {"success": True, "order": updated}


@app.post("/orders/{order_id}/resend-whatsapp")
def resend_whatsapp(order_id: str):
    """Reenvía manualmente el WhatsApp de confirmación para un pedido."""
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    phone = order.get("customer_phone")
    if not phone:
        raise HTTPException(status_code=400, detail="Este pedido no tiene teléfono registrado")

    result = send_order_confirmation(
        phone=phone,
        customer_name=order.get("customer_name", "Cliente"),
        order_number=order.get("order_number", ""),
        total=order.get("total_price", "0"),
        currency=order.get("currency", "COP"),
    )

    mark_whatsapp_sent(
        order_id=order_id,
        success=result["success"],
        message_id=result.get("message_id"),
        error=result.get("error"),
    )

    if result["success"]:
        return {"success": True, "message": "WhatsApp reenviado correctamente"}
    else:
        raise HTTPException(status_code=502, detail=f"Error al enviar WhatsApp: {result['error']}")


@app.get("/stats")
def dashboard_stats():
    """Estadísticas del dashboard CRM."""
    return get_dashboard_stats()


# ────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
