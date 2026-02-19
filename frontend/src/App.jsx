// App.jsx — COPAS CRM Application
import { useState } from 'react'
import './index.css'
import OrdersList from './pages/OrdersList'
import OrderDetail from './pages/OrderDetail'

const NAV_ITEMS = [
  { key: 'orders', label: 'Pedidos', icon: '📦' },
  { key: 'customers', label: 'Clientes', icon: '👥', disabled: true },
  { key: 'whatsapp', label: 'WhatsApp', icon: '💬', disabled: true },
  { key: 'settings', label: 'Configuración', icon: '⚙️', disabled: true },
]

function ComingSoon({ label }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">🚧</div>
      <div className="empty-title">{label}</div>
      <div className="empty-desc">Esta sección estará disponible próximamente.</div>
    </div>
  )
}

export default function App() {
  const [activePage, setActivePage] = useState('orders')
  const [selectedOrderId, setSelectedOrderId] = useState(null)

  function handleSelectOrder(id) {
    setSelectedOrderId(id)
    setActivePage('order-detail')
  }

  function handleBackToList() {
    setSelectedOrderId(null)
    setActivePage('orders')
  }

  function renderPage() {
    if (activePage === 'order-detail' && selectedOrderId) {
      return <OrderDetail orderId={selectedOrderId} onBack={handleBackToList} />
    }
    switch (activePage) {
      case 'orders':
        return <OrdersList onSelectOrder={handleSelectOrder} />
      default:
        return <ComingSoon label={NAV_ITEMS.find(n => n.key === activePage)?.label || 'Sección'} />
    }
  }

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-text">COPAS CRM</div>
          <div className="logo-sub">Powered by Shopify + WhatsApp</div>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              className={`nav-item ${activePage === item.key || (item.key === 'orders' && activePage === 'order-detail') ? 'active' : ''}`}
              onClick={() => {
                if (!item.disabled) {
                  setActivePage(item.key)
                  setSelectedOrderId(null)
                }
              }}
              disabled={item.disabled}
              style={{ opacity: item.disabled ? 0.4 : 1 }}
              title={item.disabled ? 'Próximamente' : item.label}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
              {item.disabled && <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-muted)' }}>Pronto</span>}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          v1.0.0 · COPAS
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        {renderPage()}
      </main>
    </div>
  )
}
