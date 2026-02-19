// api.js — Thin wrapper para llamadas al backend

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
    const res = await fetch(`${BASE}${path}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Error del servidor');
    }
    return res.json();
}

export const api = {
    // Pedidos
    getOrders: (params = {}) => {
        const qs = new URLSearchParams(
            Object.fromEntries(Object.entries(params).filter(([, v]) => v != null))
        ).toString();
        return request(`/orders${qs ? `?${qs}` : ''}`);
    },

    getOrder: (id) => request(`/orders/${id}`),

    updateStatus: (id, status, notes) =>
        request(`/orders/${id}/status`, {
            method: 'PATCH',
            body: JSON.stringify({ status, notes }),
        }),

    resendWhatsApp: (id) =>
        request(`/orders/${id}/resend-whatsapp`, { method: 'POST' }),

    // Stats
    getStats: () => request('/stats'),

    // Health
    health: () => request('/health'),
};
