"""
models.py — Schemas Pydantic para validación de datos
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class CustomerData(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class ShippingAddress(BaseModel):
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None  # Fallback si customer.phone está vacío


class LineItem(BaseModel):
    name: str
    quantity: int
    price: str
    sku: Optional[str] = None
    variant_title: Optional[str] = None


class ShopifyOrderPayload(BaseModel):
    """
    Payload que Make enviará al endpoint /webhook/shopify
    Make debe mapear los campos del webhook de Shopify a este formato.
    """
    shopify_order_id: str
    order_number: str
    customer: Optional[CustomerData] = None
    shipping_address: Optional[ShippingAddress] = None
    line_items: List[LineItem] = []
    total_price: str
    currency: str = "COP"
    financial_status: Optional[str] = None   # paid, pending, etc.
    fulfillment_status: Optional[str] = None  # null, fulfilled, etc.
    note: Optional[str] = None
    tags: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    """Para actualizar el estado de un pedido desde el CRM"""
    status: str  # nuevo, en_proceso, enviado, completado, cancelado
    notes: Optional[str] = None


class OrderFilter(BaseModel):
    status: Optional[str] = None
    whatsapp_sent: Optional[bool] = None
    limit: int = 50
    offset: int = 0
