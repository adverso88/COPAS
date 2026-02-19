// OrderDetail.jsx — Vista de detalle de un pedido
import { useState, useEffect } from 'react';
import { api } from '../api';

const STATUS_OPTIONS = [
    { value: 'nuevo', label: '🔵 Nuevo' },
    { value: 'en_proceso', label: '🟡 En proceso' },
    { value: 'enviado', label: '🟣 Enviado' },
    { value: 'completado', label: '🟢 Completado' },
    { value: 'cancelado', label: '🔴 Cancelado' },
];

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('es-CO', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function formatPrice(price, currency = 'COP') {
    const num = parseFloat(price);
    if (isNaN(num)) return price;
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency }).format(num);
}

function Toast({ msg, type, onClose }) {
    useEffect(() => {
        const t = setTimeout(onClose, 3500);
        return () => clearTimeout(t);
    }, [onClose]);
    return <div className={`toast ${type}`}>{msg}</div>;
}

export default function OrderDetail({ orderId, onBack }) {
    const [order, setOrder] = useState(null);
    const [loading, setLoading] = useState(true);
    const [selectedStatus, setSelectedStatus] = useState('');
    const [notes, setNotes] = useState('');
    const [saving, setSaving] = useState(false);
    const [sending, setSending] = useState(false);
    const [toast, setToast] = useState(null);

    useEffect(() => {
        setLoading(true);
        api.getOrder(orderId)
            .then((data) => {
                setOrder(data);
                setSelectedStatus(data.status);
                setNotes(data.notes || '');
            })
            .catch((e) => setToast({ msg: e.message, type: 'error' }))
            .finally(() => setLoading(false));
    }, [orderId]);

    const handleSaveStatus = async () => {
        setSaving(true);
        try {
            await api.updateStatus(orderId, selectedStatus, notes);
            setOrder((o) => ({ ...o, status: selectedStatus, notes }));
            setToast({ msg: '✅ Estado actualizado', type: 'success' });
        } catch (e) {
            setToast({ msg: `❌ ${e.message}`, type: 'error' });
        } finally {
            setSaving(false);
        }
    };

    const handleResendWhatsApp = async () => {
        setSending(true);
        try {
            await api.resendWhatsApp(orderId);
            setToast({ msg: '✅ WhatsApp reenviado correctamente', type: 'success' });
            // Recargar para ver nuevo log
            const updated = await api.getOrder(orderId);
            setOrder(updated);
        } catch (e) {
            setToast({ msg: `❌ ${e.message}`, type: 'error' });
        } finally {
            setSending(false);
        }
    };

    if (loading) {
        return (
            <div className="loading-spinner">
                <div className="spinner" /> Cargando pedido...
            </div>
        );
    }

    if (!order) {
        return (
            <div className="empty-state">
                <div className="empty-icon">😕</div>
                <div className="empty-title">Pedido no encontrado</div>
                <button className="btn btn-ghost" onClick={onBack}>← Volver</button>
            </div>
        );
    }

    const address = order.shipping_address || {};
    const lineItems = order.line_items || [];
    const wspLogs = order.whatsapp_logs || [];

    return (
        <div>
            {/* Header */}
            <div className="page-header">
                <div>
                    <button className="btn btn-ghost btn-sm" onClick={onBack} style={{ marginBottom: 8 }}>
                        ← Volver
                    </button>
                    <div className="page-title">Pedido {order.order_number}</div>
                    <div className="page-subtitle">Shopify ID: {order.shopify_order_id}</div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                    {order.customer_phone && (
                        <button
                            className="btn btn-whatsapp"
                            onClick={handleResendWhatsApp}
                            disabled={sending}
                        >
                            {sending ? '⏳ Enviando...' : '💬 Reenviar WhatsApp'}
                        </button>
                    )}
                </div>
            </div>

            <div className="order-detail-grid">
                {/* Columna izquierda */}
                <div>
                    {/* Información del cliente */}
                    <div className="detail-card">
                        <div className="detail-card-title">👤 Cliente</div>
                        <div className="detail-row">
                            <span className="label">Nombre</span>
                            <span className="value">{order.customer_name || '—'}</span>
                        </div>
                        <div className="detail-row">
                            <span className="label">Email</span>
                            <span className="value">{order.customer_email || '—'}</span>
                        </div>
                        <div className="detail-row">
                            <span className="label">Teléfono</span>
                            <span className="value" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                                {order.customer_phone || (
                                    <span style={{ color: 'var(--danger)', fontSize: 12 }}>Sin teléfono — sin WhatsApp</span>
                                )}
                            </span>
                        </div>
                        {address.address1 && (
                            <>
                                <div className="detail-row">
                                    <span className="label">Dirección</span>
                                    <span className="value">{address.address1}</span>
                                </div>
                                <div className="detail-row">
                                    <span className="label">Ciudad</span>
                                    <span className="value">{[address.city, address.province, address.country].filter(Boolean).join(', ')}</span>
                                </div>
                            </>
                        )}
                    </div>

                    {/* Productos */}
                    <div className="detail-card">
                        <div className="detail-card-title">🛒 Productos ({lineItems.length})</div>
                        {lineItems.length === 0 ? (
                            <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Sin productos registrados</div>
                        ) : (
                            lineItems.map((item, i) => (
                                <div key={i} className="product-item">
                                    <div>
                                        <div className="product-name">{item.name}</div>
                                        <div className="product-qty">
                                            Cant: {item.quantity}
                                            {item.variant_title ? ` · ${item.variant_title}` : ''}
                                            {item.sku ? ` · SKU: ${item.sku}` : ''}
                                        </div>
                                    </div>
                                    <div className="product-price">
                                        {formatPrice(parseFloat(item.price) * item.quantity, order.currency)}
                                    </div>
                                </div>
                            ))
                        )}
                        <div className="detail-row" style={{ marginTop: 12 }}>
                            <span className="label" style={{ fontWeight: 600 }}>Total</span>
                            <span style={{ color: 'var(--accent-light)', fontWeight: 700, fontSize: 18 }}>
                                {formatPrice(order.total_price, order.currency)}
                            </span>
                        </div>
                    </div>

                    {/* Info del pedido */}
                    <div className="detail-card">
                        <div className="detail-card-title">📋 Detalles del pedido</div>
                        <div className="detail-row">
                            <span className="label">Estado de pago</span>
                            <span className="value">{order.financial_status || '—'}</span>
                        </div>
                        <div className="detail-row">
                            <span className="label">Estado de envío (Shopify)</span>
                            <span className="value">{order.fulfillment_status || 'Sin enviar'}</span>
                        </div>
                        <div className="detail-row">
                            <span className="label">Creado</span>
                            <span className="value">{formatDate(order.created_at)}</span>
                        </div>
                        <div className="detail-row">
                            <span className="label">Actualizado</span>
                            <span className="value">{formatDate(order.updated_at)}</span>
                        </div>
                        {order.tags && (
                            <div className="detail-row">
                                <span className="label">Tags</span>
                                <span className="value">{order.tags}</span>
                            </div>
                        )}
                        {order.notes && (
                            <div style={{ marginTop: 12, color: 'var(--text-secondary)', fontSize: 14 }}>
                                <strong>Nota del cliente:</strong> {order.notes}
                            </div>
                        )}
                    </div>
                </div>

                {/* Columna derecha */}
                <div>
                    {/* Gestión de estado CRM */}
                    <div className="detail-card">
                        <div className="detail-card-title">⚙️ Gestión CRM</div>
                        <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                            Estado del pedido
                        </label>
                        <select
                            className="status-select"
                            value={selectedStatus}
                            onChange={(e) => setSelectedStatus(e.target.value)}
                        >
                            {STATUS_OPTIONS.map((opt) => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                        <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6, marginTop: 12 }}>
                            Notas internas
                        </label>
                        <textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="Anotaciones internas del equipo..."
                            style={{
                                width: '100%',
                                background: 'var(--bg-elevated)',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--radius-sm)',
                                color: 'var(--text-primary)',
                                padding: '8px 12px',
                                fontSize: 13,
                                fontFamily: 'inherit',
                                resize: 'vertical',
                                minHeight: 80,
                                marginBottom: 12,
                            }}
                        />
                        <button
                            className="btn btn-primary"
                            style={{ width: '100%' }}
                            onClick={handleSaveStatus}
                            disabled={saving}
                        >
                            {saving ? '⏳ Guardando...' : '💾 Guardar cambios'}
                        </button>
                    </div>

                    {/* Estado WhatsApp */}
                    <div className="detail-card">
                        <div className="detail-card-title">💬 WhatsApp</div>
                        <div className="detail-row">
                            <span className="label">Enviado automático</span>
                            <span>
                                {order.whatsapp_sent
                                    ? <span className="badge badge-wsp-yes">✅ Sí</span>
                                    : <span className="badge badge-wsp-no">❌ No</span>}
                            </span>
                        </div>
                        {order.whatsapp_sent_at && (
                            <div className="detail-row">
                                <span className="label">Enviado el</span>
                                <span className="value">{formatDate(order.whatsapp_sent_at)}</span>
                            </div>
                        )}

                        {/* Historial de logs */}
                        {wspLogs.length > 0 && (
                            <div style={{ marginTop: 16 }}>
                                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                    Historial
                                </div>
                                {wspLogs.slice().reverse().map((log, i) => (
                                    <div key={i} className="wsp-log-item">
                                        <div className="wsp-log-time">{formatDate(log.sent_at)}</div>
                                        <div className="wsp-log-status">
                                            {log.success
                                                ? <span className="badge badge-wsp-yes" style={{ fontSize: 11 }}>✅ Enviado {log.message_id ? `· ID: ${log.message_id.slice(-8)}` : ''}</span>
                                                : <span className="badge badge-wsp-no" style={{ fontSize: 11 }}>❌ {log.error_message || 'Error'}</span>}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {!order.customer_phone && (
                            <div style={{ marginTop: 12, fontSize: 13, color: 'var(--text-muted)', padding: '10px 12px', background: 'var(--danger-bg)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(239,68,68,0.2)' }}>
                                ⚠️ Este pedido no tiene número de teléfono. Solicita el número al cliente para poder enviar WhatsApp.
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Toast */}
            {toast && (
                <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)} />
            )}
        </div>
    );
}
