"""
database.py — Acceso a Supabase via API REST (postgrest-py)
Usamos httpx directamente para máxima compatibilidad con Python 3.14+
"""
import os
import httpx
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

load_dotenv()

SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY      = os.getenv("SUPABASE_SERVICE_KEY", "")

def _headers() -> Dict[str, str]:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }

def _url(table: str, query: str = "") -> str:
    base = f"{SUPABASE_URL}/rest/v1/{table}"
    return f"{base}?{query}" if query else base

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ────────────────────────────────────────────────────
# Clientes
# ────────────────────────────────────────────────────

def upsert_customer(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    email = customer_data.get("email")
    name  = customer_data.get("name", "Sin nombre")
    phone = customer_data.get("phone")

    with httpx.Client(timeout=15) as c:
        if email:
            # Buscar cliente existente por email
            r = c.get(_url("customers", f"email=eq.{email}&select=*"), headers=_headers())
            if r.status_code == 200 and r.json():
                existing = r.json()[0]
                update: Dict[str, Any] = {"updated_at": _now()}
                if name: update["name"] = name
                if phone: update["phone"] = phone
                c.patch(
                    _url("customers", f"email=eq.{email}"),
                    headers=_headers(), json=update
                )
                return {**existing, **update}

        # Insertar
        body: Dict[str, Any] = {"name": name, "created_at": _now(), "updated_at": _now()}
        if email: body["email"] = email
        if phone: body["phone"] = phone
        r = c.post(_url("customers"), headers=_headers(), json=body)
        return r.json()[0] if r.json() else {}


# ────────────────────────────────────────────────────
# Pedidos
# ────────────────────────────────────────────────────

def upsert_order(order_data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Retorna (pedido, es_nuevo)."""
    shopify_id = order_data["shopify_order_id"]
    with httpx.Client(timeout=15) as c:
        # Verificar idempotencia
        r = c.get(
            _url("orders", f"shopify_order_id=eq.{shopify_id}&select=id,shopify_order_id"),
            headers=_headers()
        )
        if r.status_code == 200 and r.json():
            return r.json()[0], False

        # Insertar
        order_data["created_at"] = _now()
        order_data["updated_at"] = _now()
        r = c.post(_url("orders"), headers=_headers(), json=order_data)
        return (r.json()[0] if r.json() else {}), True


def get_orders(
    status: Optional[str] = None,
    whatsapp_sent: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    parts = ["select=*", f"limit={limit}", f"offset={offset}", "order=created_at.desc"]
    if status:
        parts.append(f"status=eq.{status}")
    if whatsapp_sent is not None:
        val = "true" if whatsapp_sent else "false"
        parts.append(f"whatsapp_sent=eq.{val}")
    query = "&".join(parts)
    with httpx.Client(timeout=15) as c:
        r = c.get(_url("orders", query), headers=_headers())
        return r.json() if r.status_code == 200 else []


def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    with httpx.Client(timeout=15) as c:
        # Obtener pedido
        r = c.get(_url("orders", f"id=eq.{order_id}&select=*"), headers=_headers())
        if not r.json():
            return None
        order = r.json()[0]
        # Obtener logs de WhatsApp
        r2 = c.get(
            _url("whatsapp_logs", f"order_id=eq.{order_id}&select=*&order=sent_at.desc"),
            headers=_headers()
        )
        order["whatsapp_logs"] = r2.json() if r2.status_code == 200 else []
        return order


def update_order_status(
    order_id: str, status: str, notes: Optional[str] = None
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"status": status, "updated_at": _now()}
    if notes is not None:
        body["notes"] = notes
    with httpx.Client(timeout=15) as c:
        r = c.patch(
            _url("orders", f"id=eq.{order_id}"),
            headers=_headers(), json=body
        )
        return r.json()[0] if r.json() else {}


def mark_whatsapp_sent(
    order_id: str,
    success: bool,
    message_id: Optional[str] = None,
    error: Optional[str] = None,
):
    with httpx.Client(timeout=15) as c:
        # Actualizar pedido
        update: Dict[str, Any] = {"whatsapp_sent": success, "updated_at": _now()}
        if success:
            update["whatsapp_sent_at"] = _now()
        c.patch(_url("orders", f"id=eq.{order_id}"), headers=_headers(), json=update)

        # Insertar log
        log: Dict[str, Any] = {
            "order_id":    order_id,
            "success":     success,
            "message_id":  message_id,
            "error_message": error,
            "sent_at":     _now(),
        }
        c.post(_url("whatsapp_logs"), headers=_headers(), json=log)


# ────────────────────────────────────────────────────
# Stats
# ────────────────────────────────────────────────────

def get_dashboard_stats() -> Dict[str, Any]:
    h = {**_headers(), "Prefer": "count=exact"}
    with httpx.Client(timeout=15) as c:
        total   = c.get(_url("orders", "select=id"), headers=h)
        nuevos  = c.get(_url("orders", "status=eq.nuevo&select=id"), headers=h)
        enviado = c.get(_url("orders", "status=eq.enviado&select=id"), headers=h)
        sin_wsp = c.get(_url("orders", "whatsapp_sent=eq.false&select=id"), headers=h)

    def count(r: httpx.Response) -> int:
        cr = r.headers.get("content-range", "")
        if cr and "/" in cr:
            try: return int(cr.split("/")[1])
            except: pass
        try: return len(r.json())
        except: return 0

    return {
        "total_orders":    count(total),
        "new_orders":      count(nuevos),
        "shipped_orders":  count(enviado),
        "pending_whatsapp": count(sin_wsp),
    }
