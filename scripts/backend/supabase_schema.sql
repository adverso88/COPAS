-- ============================================================
-- COPAS CRM — Schema de Base de Datos Supabase
-- Ejecutar en el SQL Editor de Supabase
-- ============================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ────────────────────────────────────────────────────
-- Tabla: customers (clientes deduplicados)
-- ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    email       TEXT UNIQUE,          -- Clave de deduplicación
    phone       TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índice para búsqueda rápida por email y teléfono
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);

-- ────────────────────────────────────────────────────
-- Tabla: orders (pedidos del CRM)
-- ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Referencia a Shopify (único, para idempotencia)
    shopify_order_id    TEXT UNIQUE NOT NULL,
    order_number        TEXT NOT NULL,
    
    -- Cliente (referencia + copia para consulta rápida)
    customer_id         UUID REFERENCES customers(id) ON DELETE SET NULL,
    customer_name       TEXT,
    customer_email      TEXT,
    customer_phone      TEXT,
    
    -- Dirección de envío (jsonb para flexibilidad)
    shipping_address    JSONB DEFAULT '{}',
    
    -- Productos del pedido
    line_items          JSONB DEFAULT '[]',
    
    -- Financiero
    total_price         TEXT NOT NULL,
    currency            TEXT DEFAULT 'COP',
    financial_status    TEXT,          -- paid, pending, refunded, etc.
    fulfillment_status  TEXT,          -- null, fulfilled, partial, etc.
    
    -- Estado CRM interno
    status              TEXT DEFAULT 'nuevo' CHECK (
        status IN ('nuevo', 'en_proceso', 'enviado', 'completado', 'cancelado')
    ),
    
    -- WhatsApp
    whatsapp_sent       BOOLEAN DEFAULT FALSE,
    whatsapp_sent_at    TIMESTAMP WITH TIME ZONE,
    
    -- Notas y etiquetas
    notes               TEXT,
    tags                TEXT,
    
    -- Timestamps
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para queries frecuentes
CREATE INDEX IF NOT EXISTS idx_orders_shopify_id    ON orders(shopify_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_status        ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id   ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_whatsapp_sent ON orders(whatsapp_sent);
CREATE INDEX IF NOT EXISTS idx_orders_created_at    ON orders(created_at DESC);

-- ────────────────────────────────────────────────────
-- Tabla: whatsapp_logs (historial de mensajes enviados)
-- ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS whatsapp_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id        UUID REFERENCES orders(id) ON DELETE CASCADE,
    success         BOOLEAN NOT NULL,
    message_id      TEXT,              -- ID de Meta para tracking
    error_message   TEXT,              -- Detalle del error si falló
    sent_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_logs_order_id ON whatsapp_logs(order_id);

-- ────────────────────────────────────────────────────
-- Trigger: auto-actualizar updated_at
-- ────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ────────────────────────────────────────────────────
-- Row Level Security (RLS) — Desactivado para uso con Service Key
-- El backend usa SUPABASE_SERVICE_KEY que bypasea RLS
-- Si expones la anon key al frontend, activa RLS con políticas apropiadas
-- ────────────────────────────────────────────────────
-- ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE whatsapp_logs ENABLE ROW LEVEL SECURITY;

-- Vista útil para el CRM (pedidos con resumen de WhatsApp)
CREATE OR REPLACE VIEW orders_summary AS
SELECT 
    o.id,
    o.order_number,
    o.shopify_order_id,
    o.customer_name,
    o.customer_email,
    o.customer_phone,
    o.total_price,
    o.currency,
    o.status,
    o.financial_status,
    o.whatsapp_sent,
    o.whatsapp_sent_at,
    array_length(o.line_items::json[], 1) as items_count,
    o.created_at,
    o.updated_at
FROM orders o
ORDER BY o.created_at DESC;
