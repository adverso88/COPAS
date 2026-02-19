# SOP: Shopify CRM + WhatsApp Auto-Confirmación de Pedidos

## Objetivo
Construir un sistema que:
1. Reciba pedidos de Shopify vía Make (Integromat)
2. Los almacene en Supabase como un CRM de pedidos
3. Envíe automáticamente un mensaje de WhatsApp al cliente para confirmar su pedido
4. Exponga un dashboard web (CRM) para gestionar los pedidos

---

## Arquitectura General

```
Shopify (nuevo pedido)
    ↓
Make (Integromat) — ya configurado
    ↓  [HTTP POST con datos del pedido]
Backend FastAPI (Python)  ← ESTE PROYECTO
    ├── Guarda pedido en Supabase (CRM)
    └── Envía WhatsApp via Meta Cloud API
    
Frontend React/Vite
    └── Dashboard CRM (visualiza y gestiona pedidos)
```

---

## Módulos del Sistema

### Módulo 1: Backend API (FastAPI)
**Archivo:** `scripts/backend/main.py`
- Endpoint POST `/webhook/shopify` — recibe pedidos de Make
- Endpoint GET `/orders` — lista pedidos (para el frontend)
- Endpoint PATCH `/orders/{id}` — actualizar estado del pedido
- Endpoint GET `/orders/{id}` — detalle de un pedido
- Validación opcional con secret token en header `X-Webhook-Token`

### Módulo 2: CRM en Supabase
**Entidades:**
- `orders` — tabla principal de pedidos
- `customers` — tabla de clientes (deduplicados por email/teléfono)
- `whatsapp_logs` — registro de mensajes enviados

**Campos críticos de `orders`:**
- id, shopify_order_id, order_number, status
- customer_name, customer_email, customer_phone
- shipping_address (jsonb)
- line_items (jsonb) — productos del pedido
- total_price, currency
- whatsapp_sent (boolean), whatsapp_sent_at
- notes, tags
- created_at, updated_at

### Módulo 3: WhatsApp Integration (Meta Cloud API)
**Archivo:** `scripts/whatsapp/whatsapp_service.py`
- Usar Meta Cloud API (gratuita, requiere número verificado)
- Alternativa: Twilio WhatsApp (más fácil de configurar, tiene costo)
- Enviar mensaje de plantilla aprobada (Template Message)
- Los mensajes de confirmación DEBEN usar plantillas pre-aprobadas por Meta

### Módulo 4: Frontend CRM Dashboard
**Directorio:** `frontend/`
- Framework: Vite + React
- Vista: Lista de pedidos con filtros por estado
- Vista: Detalle de pedido con historial de WhatsApp
- Acción: Reenviar mensaje de WhatsApp manualmente
- Acción: Cambiar estado del pedido (Nuevo, En proceso, Enviado, Completado, Cancelado)

---

## Entradas (datos que llegan desde Make/Shopify)

El payload que Make enviará al backend (extraído del webhook de Shopify):
```json
{
  "shopify_order_id": "123456789",
  "order_number": "#1001",
  "customer": {
    "first_name": "Juan",
    "last_name": "Pérez",
    "email": "juan@ejemplo.com",
    "phone": "+573001234567"
  },
  "shipping_address": {
    "address1": "Calle 123",
    "city": "Bogotá",
    "country": "Colombia"
  },
  "line_items": [
    {"name": "Producto X", "quantity": 2, "price": "15000"}
  ],
  "total_price": "30000",
  "currency": "COP",
  "financial_status": "paid",
  "fulfillment_status": null,
  "note": "",
  "tags": ""
}
```

---

## Salidas
1. Pedido guardado en Supabase con estado "nuevo"
2. Mensaje de WhatsApp enviado al cliente
3. Log del mensaje guardado en `whatsapp_logs`
4. Confirmación HTTP 200 a Make

---

## Lógica de Procesamiento (Backend)

### Flujo al recibir un pedido:
1. Validar token de seguridad en header
2. Validar estructura del payload (Pydantic)
3. Deduplicar cliente por email → crear/actualizar en `customers`
4. Insertar pedido en `orders` (idempotente por `shopify_order_id`)
5. Verificar si el cliente tiene teléfono
   - Si tiene teléfono: enviar WhatsApp → marcar `whatsapp_sent=true`
   - Si NO tiene teléfono: marcar `whatsapp_sent=false`, guardar nota
6. Retornar `{"success": true, "order_id": "uuid"}`

### Idempotencia:
- Si llega un pedido con el mismo `shopify_order_id`, NO duplicar.
- Usar UPSERT en Supabase con `shopify_order_id` como clave única.

---

## Configuración Make (Integromat)

### Escenario a crear en Make:
1. **Trigger:** Shopify → Watch Orders (evento: Order Creation)
2. **Action:** HTTP → Make a Request
   - URL: `https://tu-backend.railway.app/webhook/shopify`
   - Method: POST
   - Headers: `X-Webhook-Token: {{TU_SECRET}}`
   - Body (JSON): mapear campos de Shopify al formato del backend

### Mapeo crítico en Make:
- `customer.phone` puede estar vacío en Shopify Basic → manejar null
- `shipping_address.phone` como fallback si `customer.phone` es null
- El número de teléfono debe incluir código de país para WhatsApp

---

## WhatsApp: Configuración Meta Cloud API

### Pre-requisitos:
1. Cuenta Meta Business verificada
2. Número de teléfono dedicado (no puede ser el número personal activo en WhatsApp)
3. Plantilla de mensaje aprobada por Meta (puede tardar 24-48h)

### Plantilla de confirmación sugerida:
```
Nombre: order_confirmation
Categoría: UTILITY
Idioma: es (Español)

Cuerpo:
"¡Hola {{1}}! 👋 Recibimos tu pedido {{2}} por un total de {{3}}. 
Pronto te confirmaremos el envío. ¡Gracias por tu compra! 🛒"
```
Variables: [nombre_cliente, numero_pedido, total]

### Variables de entorno necesarias (.env):
```
WHATSAPP_PHONE_NUMBER_ID=xxx
WHATSAPP_BUSINESS_ACCOUNT_ID=xxx
WHATSAPP_ACCESS_TOKEN=xxx
WHATSAPP_TEMPLATE_NAME=order_confirmation
WHATSAPP_TEMPLATE_LANGUAGE=es
```

---

## Variables de Entorno (.env)

```
# Backend
WEBHOOK_SECRET_TOKEN=token_secreto_aleatorio
PORT=8000

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx

# WhatsApp Meta Cloud API
WHATSAPP_PHONE_NUMBER_ID=xxx
WHATSAPP_ACCESS_TOKEN=xxx
WHATSAPP_TEMPLATE_NAME=order_confirmation
WHATSAPP_TEMPLATE_LANGUAGE=es

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Restricciones y Casos Borde

### Shopify Basic Plan:
- **MITO PARCIAL:** El dueño de la tienda SÍ recibe datos personales en los webhooks propios.
- La restricción "Protected Customer Data" aplica a apps publicadas en la App Store de Shopify, NO a webhooks propios del merchant.
- Sin embargo, algunos campos como `customer.phone` pueden estar vacíos si el cliente no lo proporcionó en el checkout.
- **Solución:** Revisar `customer.phone` Y `shipping_address.phone` como fallback.
- Si ambos son null, guardar el pedido sin WhatsApp y marcar para seguimiento manual.

### WhatsApp:
- Solo se pueden enviar mensajes a usuarios que tengan el número registrado en WhatsApp.
- Meta requiere plantillas aprobadas para mensajes iniciados por el negocio (outbound).
- La ventana de 24h de respuesta libre NO aplica para mensajes iniciados por el negocio.
- Twilio WhatsApp Sandbox es útil para pruebas sin esperar aprobación de Meta.

### Despliegue:
- El backend debe ser accesible desde internet (para Make y para el frontend).
- Opciones de hosting gratuito: Railway.app, Render.com, Fly.io.
- Supabase tiene tier gratuito suficiente para comenzar.

---

## Dependencias (requirements.txt)
```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
python-dotenv>=1.0.0
httpx>=0.27.0
pydantic>=2.6.0
python-multipart>=0.0.9
```

### ⚠️ Nota Python 3.14 + supabase-py:
- La librería `supabase` arrastra `pyiceberg` y `pyroaring` que requieren compilar extensiones C++ con Rust.
- **En Python 3.14, estas extensiones NO tienen wheel precompilado** → falla la instalación.
- **Solución:** NO usar `supabase`. En cambio, usar `httpx` directamente contra la API REST de Supabase.
- El archivo `database.py` implementa esta solución con httpx puro.

---

## Estructura de Archivos del Proyecto
```
COPAS/
├── directivas/
│   └── shopify_crm_whatsapp_SOP.md   ← ESTE ARCHIVO
├── scripts/
│   └── backend/
│       ├── main.py                    ← FastAPI app
│       ├── models.py                  ← Pydantic schemas
│       ├── database.py                ← Supabase client
│       └── whatsapp_service.py        ← WhatsApp integration
├── frontend/                          ← React/Vite CRM dashboard
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── OrdersList.jsx
│   │   │   └── OrderDetail.jsx
│   │   └── components/
├── .env                               ← Variables de entorno
├── requirements.txt
└── README.md
```

---

## Orden de Implementación

1. ✅ Crear directiva (este archivo)
2. ✅ Crear SQL schema para Supabase (`supabase_schema.sql`)
3. ✅ Construir backend FastAPI (`main.py`, `models.py`, `database.py`)
4. ✅ Integrar WhatsApp service (`whatsapp_service.py`)
5. ✅ Construir frontend CRM (React/Vite con `OrdersList.jsx`, `OrderDetail.jsx`)
6. ⬜ Ejecutar `supabase_schema.sql` en Supabase SQL Editor
7. ⬜ Rellenar `.env` con credenciales reales
8. ⬜ Configurar escenario en Make
9. ⬜ Crear plantilla de WhatsApp en Meta Business
10. ⬜ Desplegar backend en Railway/Render
11. ⬜ Desplegar frontend en Vercel
12. ⬜ Pruebas end-to-end
