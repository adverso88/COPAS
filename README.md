# COPAS CRM 🛒💬

CRM de pedidos Shopify con confirmación automática por WhatsApp.

## Arquitectura

```
Shopify → Make (Integromat) → Backend FastAPI → Supabase
                                              → WhatsApp (Meta Cloud API)
                                 ↑
                           Frontend React CRM
```

---

## ⚡ Inicio Rápido

### 1. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env con tus credenciales reales
```

### 2. Instalar dependencias Python

```bash
pip install -r requirements.txt
```

### 3. Configurar base de datos en Supabase

1. Abre [supabase.com](https://supabase.com) → tu proyecto → SQL Editor
2. Ejecuta el contenido de `scripts/backend/supabase_schema.sql`

### 4. Iniciar el backend

```bash
python scripts/backend/main.py
# → http://localhost:8000
# → Docs: http://localhost:8000/docs
```

### 5. Iniciar el frontend

```bash
cd frontend
npm install  # si es la primera vez
npm run dev
# → http://localhost:5173
```

---

## 📋 Configurar Make (Integromat)

1. En Make, crea un nuevo **Escenario**
2. **Trigger:** `Shopify → Watch Orders`
3. **Action:** `HTTP → Make a Request`
   - **URL:** `http://localhost:8000/webhook/shopify` (en producción: tu URL de Railway/Render)
   - **Method:** POST
   - **Headers:**
     - `Content-Type: application/json`
     - `X-Webhook-Token: [tu WEBHOOK_SECRET_TOKEN del .env]`
   - **Body type:** Raw (JSON)
   - **Body:** Mapear los campos de Shopify:

```json
{
  "shopify_order_id": "{{id}}",
  "order_number": "#{{order_number}}",
  "customer": {
    "first_name": "{{customer.first_name}}",
    "last_name": "{{customer.last_name}}",
    "email": "{{customer.email}}",
    "phone": "{{customer.phone}}"
  },
  "shipping_address": {
    "address1": "{{shipping_address.address1}}",
    "city": "{{shipping_address.city}}",
    "province": "{{shipping_address.province}}",
    "country": "{{shipping_address.country}}",
    "phone": "{{shipping_address.phone}}"
  },
  "line_items": "{{line_items}}",
  "total_price": "{{total_price}}",
  "currency": "{{currency}}",
  "financial_status": "{{financial_status}}",
  "fulfillment_status": "{{fulfillment_status}}",
  "note": "{{note}}",
  "tags": "{{tags}}"
}
```

---

## 💬 Configurar WhatsApp (Meta Cloud API)

1. Ve a [developers.facebook.com](https://developers.facebook.com)
2. Crea una App → tipo **Business**
3. Agrega el producto **WhatsApp**
4. En **Getting Started**: copia tu `Phone Number ID` y `Access Token`
5. Crea una plantilla de mensaje en **Message Templates**:

| Campo | Valor |
|-------|-------|
| Nombre | `order_confirmation` |
| Categoría | UTILITY |
| Idioma | Español (es) |
| Cuerpo | `¡Hola {{1}}! 👋 Recibimos tu pedido {{2}} por un total de {{3}}. Pronto te confirmamos el envío. ¡Gracias! 🛒` |

6. Espera aprobación de Meta (24-48h)
7. Agrega los valores al `.env`

**Alternativa rápida para pruebas:** Usa **Twilio WhatsApp Sandbox** (funciona sin esperar aprobación)

---

## 🚀 Despliegue en Producción

### Backend → Railway.app (recomendado, gratis)
1. Ve a [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Selecciona este repo → configurar variables de entorno
3. En Settings → Source: `scripts/backend/main.py`
4. Agrega un `Procfile` en la raíz: `web: uvicorn scripts.backend.main:app --host 0.0.0.0 --port $PORT`

### Frontend → Vercel (gratis)
1. Ve a [vercel.com](https://vercel.com) → Import Git Repository
2. Directorio raíz: `frontend`
3. Agrega variable: `VITE_API_URL=https://tu-backend.railway.app`

---

## 📁 Estructura

```
COPAS/
├── directivas/
│   └── shopify_crm_whatsapp_SOP.md  # Fuente de la verdad
├── scripts/backend/
│   ├── main.py                      # API FastAPI
│   ├── models.py                    # Schemas Pydantic
│   ├── database.py                  # Acceso a Supabase
│   ├── whatsapp_service.py          # Meta Cloud API
│   └── supabase_schema.sql          # Crear tablas en Supabase
├── frontend/src/
│   ├── App.jsx                      # App principal
│   ├── api.js                       # Cliente API
│   └── pages/
│       ├── OrdersList.jsx           # Vista lista de pedidos
│       └── OrderDetail.jsx          # Vista detalle del pedido
├── .env.example                     # Plantilla de variables
├── requirements.txt
└── README.md
```

---

## 🔌 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/webhook/shopify` | Recibe pedidos de Make |
| GET | `/orders` | Lista pedidos (con filtros) |
| GET | `/orders/{id}` | Detalle de un pedido |
| PATCH | `/orders/{id}/status` | Actualizar estado CRM |
| POST | `/orders/{id}/resend-whatsapp` | Reenviar WhatsApp |
| GET | `/stats` | Estadísticas del dashboard |

**Documentación interactiva:** `http://localhost:8000/docs`

---

## ⚠️ Notas Shopify Basic

- El dueño de la tienda **SÍ recibe** datos completos del cliente en webhooks propios
- La restricción de "Protected Customer Data" es para apps del Marketplace, no para ti
- `customer.phone` puede estar vacío si el cliente no lo puso en el checkout
- El backend usa `shipping_address.phone` como fallback automático
