
import React from 'react'
import { Routes, Route, useNavigate, Navigate } from 'react-router-dom'
import AdminLogin from './pages/AdminLogin'
import AdminDashboard from './pages/AdminDashboard'
import './App.css'
import Page5 from './pages/Page5'

const API_URL = 'http://127.0.0.1:8000'

function WelcomePage() {
  const navigate = useNavigate()

  return (
    <div className="welcome-page">
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">E</div>
          <span>
            EKR
            <small>Enterprise Knowledge Retrieval</small>
          </span>
        </div>
        <span className="system-status">
          <span className="status-dot"></span>
          Secure Knowledge Access
        </span>
      </header>

      <main className="welcome-container">
        <div className="welcome-content">
          <span className="eyebrow">INTELLIGENT DOCUMENT RETRIEVAL</span>

          <h1>
            Welcome to <span>EKR</span>
          </h1>

          <h2 className="role-heading">
            Enterprise Knowledge Retrieval
          </h2>

          <p className="welcome-description">
            Access your enterprise documents and get instant,
            reliable answers using AI-powered search and retrieval.
          </p>

          <div className="role-cards">
            <div className="role-card">
              <div className="role-icon admin-icon">♙</div>
              <h3>Admin Access</h3>
              <p>
                Login with your API key to manage and upload
                enterprise documents.
              </p>
              <button onClick={() => navigate('/admin-login')}>
                Go to Admin Login →
              </button>
            </div>

            <div className="role-card">
              <div className="role-icon public-icon">♧</div>
              <h3>Public Access</h3>
              <p>
                View available documents and ask questions
                using the AI knowledge assistant.
              </p>
              <button onClick={() => navigate('/public')}>
                Go to Public Access →
              </button>
            </div>
          </div>
        </div>
      </main>

      <footer className="footer">
        <span>EKR © 2026</span>
        <span>Secure · Intelligent · Reliable</span>
      </footer>
    </div>
  )
}

function ProtectedAdminDashboard() {
  const [isAuthorized, setIsAuthorized] = React.useState(null)

  React.useEffect(() => {
    const verifyAdmin = async () => {
      const key = sessionStorage.getItem('ekr_admin_api_key')

      if (!key) {
        setIsAuthorized(false)
        return
      }

      try {
        const response = await fetch(`${API_URL}/api/auth/me`, {
          headers: { 'X-API-Key': key },
        })

        if (!response.ok) {
          throw new Error('Unauthorized')
        }

        const data = await response.json()
        setIsAuthorized(data.role === 'admin')
      } catch {
        sessionStorage.removeItem('ekr_admin_api_key')
        setIsAuthorized(false)
      }
    }

    verifyAdmin()
  }, [])

  if (isAuthorized === null) {
    return <p>Verifying administrator access...</p>
  }

  return isAuthorized
    ? <AdminDashboard />
    : <Navigate to="/admin-login" replace />
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<WelcomePage />} />
      <Route path="/admin-login" element={<AdminLogin />} />
      <Route path="/admin-dashboard" element={<ProtectedAdminDashboard />} />
      <Route path="/public" element={<Page5 />} />
    </Routes>
  )
}

export default App
