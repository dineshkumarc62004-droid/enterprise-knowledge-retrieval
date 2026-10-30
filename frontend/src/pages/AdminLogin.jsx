
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import '../App.css'

const API_URL = 'http://127.0.0.1:8000'

function AdminLogin() {
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const navigate = useNavigate()

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: { 'X-API-Key': apiKey.trim() },
      })

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          throw new Error('Invalid API key.')
        }
        if (response.status === 503) {
          throw new Error('Backend API keys are not configured.')
        }
        throw new Error('Authentication failed.')
      }

      const data = await response.json()

      if (data.role !== 'admin') {
        throw new Error('Access denied. Admin key required.')
      }

      sessionStorage.setItem('ekr_admin_api_key', apiKey.trim())
      navigate('/admin-dashboard')
    } catch (err) {
      setError(
        err.message === 'Failed to fetch'
          ? 'Cannot connect to backend.'
          : err.message
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="admin-login-page">
      <header className="admin-login-navbar">
        <div className="brand">
          <div className="brand-icon">E</div>
          <span>
            EKR
            <small>Enterprise Knowledge Retrieval</small>
          </span>
        </div>
        <span>Secure Access</span>
      </header>

      <main className="admin-login-layout">
        <section className="admin-login-info">
          <div className="admin-shield">♢</div>
          <h2>Admin Portal</h2>
          <p>
            Please enter your API key to access
            the administration panel.
          </p>

          <div className="admin-login-features">
            <div>▣ <span>Upload Documents</span></div>
            <div>▦ <span>Manage Content</span></div>
            <div>▥ <span>Knowledge Retrieval</span></div>
          </div>
        </section>

        <section className="admin-login-form-area">
          <div className="admin-login-card">
            <h1>Admin Login</h1>
            <p>Enter your administrator API key to continue.</p>

            <form onSubmit={handleLogin}>
              <label htmlFor="apiKey">API Key</label>

              <input
                id="apiKey"
                type="password"
                placeholder="Enter your API key"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                required
              />

              {error && <p className="login-error">{error}</p>}

              <button type="submit" disabled={loading}>
                {loading ? 'Verifying...' : 'Login →'}
              </button>
            </form>

            <div className="authorized-note">
              ♙ Authorized personnel only
            </div>

            <button
              className="back-button"
              onClick={() => navigate('/')}
            >
              ← Back to Home
            </button>
          </div>
        </section>
      </main>
    </div>
  )
}

export default AdminLogin
