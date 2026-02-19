"""
whatsapp_service.py — Integración con Meta Cloud API (WhatsApp Business)

Documentación: https://developers.facebook.com/docs/whatsapp/cloud-api
"""
import os
import httpx
from dotenv import load_dotenv
from typing import Optional, Dict, Any

load_dotenv()

WHATSAPP_API_URL = "https://graph.facebook.com/v18.0"
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
TEMPLATE_NAME = os.getenv("WHATSAPP_TEMPLATE_NAME", "order_confirmation")
TEMPLATE_LANGUAGE = os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "es")


def normalize_phone(phone: str) -> str:
    """
    Normaliza un número de teléfono para WhatsApp.
    WhatsApp requiere formato internacional sin '+' ni espacios.
    Ejemplos:
      +57 300-123-4567  → 573001234567
      3001234567        → 573001234567 (asume Colombia por defecto)
      +1-555-123-4567   → 15551234567
    """
    # Remover caracteres no numéricos excepto '+'
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")

    # Remover el '+' si está al inicio
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]

    # Si es un número colombiano sin código de país (10 dígitos empezando en 3)
    if len(cleaned) == 10 and cleaned.startswith("3"):
        cleaned = "57" + cleaned

    return cleaned


def send_order_confirmation(
    phone: str,
    customer_name: str,
    order_number: str,
    total: str,
    currency: str = "COP",
) -> Dict[str, Any]:
    """
    Envía mensaje de confirmación de pedido usando plantilla de Meta.
    
    IMPORTANTE: La plantilla debe estar aprobada en Meta Business Manager.
    Nombre de plantilla: WHATSAPP_TEMPLATE_NAME (env var)
    
    Variables de la plantilla:
    {{1}} = nombre del cliente
    {{2}} = número de pedido
    {{3}} = total con moneda
    
    Retorna: {"success": bool, "message_id": str | None, "error": str | None}
    """
    if not PHONE_NUMBER_ID or not ACCESS_TOKEN:
        return {
            "success": False,
            "message_id": None,
            "error": "WhatsApp no configurado: faltan WHATSAPP_PHONE_NUMBER_ID o WHATSAPP_ACCESS_TOKEN en .env",
        }

    normalized = normalize_phone(phone)
    if not normalized or len(normalized) < 10:
        return {
            "success": False,
            "message_id": None,
            "error": f"Número de teléfono inválido: '{phone}'",
        }

    # Formatear total
    total_formatted = f"{currency} {total}"

    payload = {
        "messaging_product": "whatsapp",
        "to": normalized,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANGUAGE},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": customer_name},
                        {"type": "text", "text": order_number},
                        {"type": "text", "text": total_formatted},
                    ],
                }
            ],
        },
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{WHATSAPP_API_URL}/{PHONE_NUMBER_ID}/messages",
                headers={
                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            message_id = None
            if "messages" in data and data["messages"]:
                message_id = data["messages"][0].get("id")

            return {
                "success": True,
                "message_id": message_id,
                "error": None,
            }

    except httpx.HTTPStatusError as e:
        error_detail = ""
        try:
            error_detail = e.response.json().get("error", {}).get("message", str(e))
        except Exception:
            error_detail = str(e)
        return {
            "success": False,
            "message_id": None,
            "error": f"HTTP {e.response.status_code}: {error_detail}",
        }
    except Exception as e:
        return {
            "success": False,
            "message_id": None,
            "error": str(e),
        }


def send_custom_message(phone: str, message_text: str) -> Dict[str, Any]:
    """
    Envía un mensaje de texto libre (solo funciona dentro de la ventana de 24h
    después de que el cliente te haya escrito primero).
    Para mensajes iniciados por el negocio, usa send_order_confirmation().
    """
    if not PHONE_NUMBER_ID or not ACCESS_TOKEN:
        return {"success": False, "error": "WhatsApp no configurado"}

    normalized = normalize_phone(phone)
    payload = {
        "messaging_product": "whatsapp",
        "to": normalized,
        "type": "text",
        "text": {"body": message_text},
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{WHATSAPP_API_URL}/{PHONE_NUMBER_ID}/messages",
                headers={
                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}
