// OrdersList.jsx — Vista principal del CRM: lista de pedidos
import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';

const STATUS_LABELS = {
    nuevo: 'Nuevo',
    en_proceso: 'En proceso',
    enviado: 'Enviado',
    completado: 'Completado',
    cancelado: 'Cancelado',
};

const STATUS_ICONS = {
    nuevo: '🔵',
    en_proceso: '🟡',
    enviado: '🟣',
    completado: '🟢',
    cancelado: '🔴',
};

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('es-CO', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function formatPrice(price, currency = 'COP') {
    const num = parseFloat(price);
    if (isNaN(num)) return price;
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency }).format(num);
}

export default function OrdersList({ onSelectOrder }) {
    const [orders, setOrders] = useState([]);
    const [stats, setStats] = useState({});
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all');
    const [wspFilter, setWspFilter] = useState('all');
    const [error, setError] = useState(null);

    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const params = {};
            if (filter !== 'all') params.status = filter;
            if (wspFilter === 'pending') params.whatsapp_sent = false;
            if (wspFilter === 'sent') params.whatsapp_sent = true;

            const [ordersRes, statsRes] = await Promise.all([
                api.getOrders(params),
                api.getStats(),
            ]);
            setOrders(ordersRes.orders || []);
            setStats(statsRes);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [filter, wspFilter]);

    useEffect(() => { loadData(); }, [loadData]);

    const FILTERS = [
        { key: 'all', label: 'Todos' },
        { key: 'nuevo', label: '🔵 Nuevos' },
        { key: 'en_proceso', label: '🟡 En proceso' },
        { key: 'enviado', label: '🟣 Enviados' },
        { key: 'completado', label: '🟢 Completados' },
        { key: 'cancelado', label: '🔴 Cancelados' },
    ];

    const WSP_FILTERS = [
        { key: 'all', label: 'Todos WhatsApp' },
        { key: 'pending', label: '❌ Sin WhatsApp' },
        { key: 'sent', label: '✅ WhatsApp enviado' },
    ];

    return (
        <div>
            {/* Stats cards */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-label">Total Pedidos</div>
                    <div className="stat-value">{stats.total_orders ?? '…'}</div>
                    <div className="stat-icon">📦</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Nuevos</div>
                    <div className="stat-value">{stats.new_orders ?? '…'}</div>
                    <div className="stat-icon">🆕</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Enviados</div>
                    <div className="stat-value">{stats.shipped_orders ?? '…'}</div>
                    <div className="stat-icon">🚚</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Sin WhatsApp</div>
                    <div className="stat-value">{stats.pending_whatsapp ?? '…'}</div>
                    <div className="stat-icon">💬</div>
                </div>
            </div>

            {/* Header */}
            <div className="page-header">
                <div>
                    <div className="page-title">Pedidos</div>
                    <div className="page-subtitle">{orders.length} pedido{orders.length !== 1 ? 's' : ''} encontrado{orders.length !== 1 ? 's' : ''}</div>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={loadData}>
                    🔄 Actualizar
                </button>
            </div>

            {/* Filters */}
            <div className="filters-bar">
                {FILTERS.map((f) => (
                    <button
                        key={f.key}
                        className={`filter-btn ${filter === f.key ? 'active' : ''}`}
                        onClick={() => setFilter(f.key)}
                    >
                        {f.label}
                    </button>
                ))}
                <div style={{ flexGrow: 1 }} />
                {WSP_FILTERS.map((f) => (
                    <button
                        key={f.key}
                        className={`filter-btn ${wspFilter === f.key ? 'active' : ''}`}
                        onClick={() => setWspFilter(f.key)}
                    >
                        {f.label}
                    </button>
                ))}
            </div>

            {/* Error */}
            {error && (
                <div className="toast error" style={{ position: 'relative', bottom: 'auto', right: 'auto', marginBottom: 16 }}>
                    ⚠️ {error} — ¿El backend está corriendo?
                </div>
            )}

            {/* Table */}
            <div className="table-container">
                {loading ? (
                    <div className="loading-spinner">
                        <div className="spinner" /> Cargando pedidos...
                    </div>
                ) : orders.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-icon">📭</div>
                        <div className="empty-title">Sin pedidos</div>
                        <div className="empty-desc">
                            Cuando Shopify envíe un nuevo pedido vía Make, aparecerá aquí.
                        </div>
                    </div>
                ) : (
                    <table className="crm-table">
                        <thead>
                            <tr>
                                <th>Pedido</th>
                                <th>Cliente</th>
                                <th>Teléfono</th>
                                <th>Total</th>
                                <th>Estado</th>
                                <th>WhatsApp</th>
                                <th>Fecha</th>
                            </tr>
                        </thead>
                        <tbody>
                            {orders.map((order) => (
                                <tr key={order.id} onClick={() => onSelectOrder(order.id)}>
                                    <td className="primary">{order.order_number}</td>
                                    <td>{order.customer_name || '—'}</td>
                                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
                                        {order.customer_phone || <span style={{ color: 'var(--danger)', fontSize: 11 }}>Sin teléfono</span>}
                                    </td>
                                    <td className="primary">{formatPrice(order.total_price, order.currency)}</td>
                                    <td>
                                        <span className={`badge badge-${order.status}`}>
                                            {STATUS_ICONS[order.status]} {STATUS_LABELS[order.status]}
                                        </span>
                                    </td>
                                    <td>
                                        {order.whatsapp_sent ? (
                                            <span className="badge badge-wsp-yes">✅ Enviado</span>
                                        ) : (
                                            <span className="badge badge-wsp-no">❌ Pendiente</span>
                                        )}
                                    </td>
                                    <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                        {formatDate(order.created_at)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
