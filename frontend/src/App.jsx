import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import './App.css'

// Point at the deployed backend; falls back to localhost for dev
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

function App() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({ source_type: '', status: '', scope: '' })
  const [uploadStatus, setUploadStatus] = useState(null)
  const [expandedRow, setExpandedRow] = useState(null)

  const fetchRecords = useCallback(() => {
    setLoading(true)
    const params = {}
    if (filters.source_type) params.source_type = filters.source_type
    if (filters.status) params.status = filters.status
    if (filters.scope) params.scope = filters.scope

    axios.get(`${API_BASE}/records/`, { params })
      .then(res => {
        // Handle paginated or flat response
        const data = res.data.results || res.data
        setRecords(data)
        setLoading(false)
        setError(null)
      })
      .catch(err => {
        console.error("Fetch error:", err)
        setError("Failed to connect to backend. Is the server running?")
        setLoading(false)
      })
  }, [filters])

  useEffect(() => { fetchRecords() }, [fetchRecords])

  // --- Workflow actions ---
  const handleApprove = (id) => {
    axios.post(`${API_BASE}/records/${id}/approve/`, { analyst: 'dashboard_user' })
      .then(() => fetchRecords())
      .catch(err => alert(err.response?.data?.error || 'Approve failed'))
  }

  const handleLock = (id) => {
    if (!window.confirm('Lock this record for audit? This cannot be undone.')) return
    axios.post(`${API_BASE}/records/${id}/lock/`, { analyst: 'dashboard_user' })
      .then(() => fetchRecords())
      .catch(err => alert(err.response?.data?.error || 'Lock failed'))
  }

  const handleFlag = (id) => {
    const reason = window.prompt('Reason for flagging:')
    if (!reason) return
    axios.post(`${API_BASE}/records/${id}/flag/`, { reason, analyst: 'dashboard_user' })
      .then(() => fetchRecords())
      .catch(err => alert(err.response?.data?.error || 'Flag failed'))
  }

  // --- File upload ---
  const handleUpload = (endpoint, e) => {
    const file = e.target.files[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    setUploadStatus('Uploading...')

    axios.post(`${API_BASE}/records/${endpoint}/`, formData)
      .then(res => {
        setUploadStatus(res.data.message)
        fetchRecords()
        setTimeout(() => setUploadStatus(null), 4000)
      })
      .catch(err => {
        setUploadStatus(`Error: ${err.response?.data?.error || err.message}`)
        setTimeout(() => setUploadStatus(null), 5000)
      })
    // Reset input so same file can be re-uploaded
    e.target.value = ''
  }

  // --- Status badge ---
  const StatusBadge = ({ status }) => {
    const colors = {
      PENDING: { bg: '#fff3e0', color: '#e65100' },
      FLAGGED: { bg: '#ffebee', color: '#b71c1c' },
      APPROVED: { bg: '#e8f5e9', color: '#1b5e20' },
      LOCKED: { bg: '#e3f2fd', color: '#0d47a1' },
    }
    const style = colors[status] || colors.PENDING
    return (
      <span className="status-badge" style={{ backgroundColor: style.bg, color: style.color }}>
        {status}
      </span>
    )
  }

  // --- Summary stats ---
  const stats = {
    total: records.length,
    pending: records.filter(r => r.status === 'PENDING').length,
    flagged: records.filter(r => r.status === 'FLAGGED').length,
    approved: records.filter(r => r.status === 'APPROVED').length,
    locked: records.filter(r => r.status === 'LOCKED').length,
  }

  if (error) {
    return (
      <div className="app-container">
        <h1>Breathe ESG — Analyst Dashboard</h1>
        <div className="error-banner">{error}</div>
      </div>
    )
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Breathe ESG — Analyst Review Dashboard</h1>
        <p className="subtitle">Ingest, review, and approve emission data before audit lock.</p>
      </header>

      {/* Upload Section */}
      <section className="upload-section">
        <h2>Ingest Data</h2>
        <div className="upload-buttons">
          <label className="upload-btn sap">
            Upload SAP CSV
            <input type="file" accept=".csv" onChange={(e) => handleUpload('upload_sap', e)} hidden />
          </label>
          <label className="upload-btn utility">
            Upload Utility CSV
            <input type="file" accept=".csv" onChange={(e) => handleUpload('upload_utility', e)} hidden />
          </label>
          <label className="upload-btn travel">
            Upload Travel JSON
            <input type="file" accept=".json" onChange={(e) => handleUpload('upload_travel', e)} hidden />
          </label>
        </div>
        {uploadStatus && <div className="upload-status">{uploadStatus}</div>}
      </section>

      {/* Stats */}
      <section className="stats-bar">
        <div className="stat">
          <span className="stat-value">{stats.total}</span>
          <span className="stat-label">Total</span>
        </div>
        <div className="stat pending">
          <span className="stat-value">{stats.pending}</span>
          <span className="stat-label">Pending</span>
        </div>
        <div className="stat flagged">
          <span className="stat-value">{stats.flagged}</span>
          <span className="stat-label">Flagged</span>
        </div>
        <div className="stat approved">
          <span className="stat-value">{stats.approved}</span>
          <span className="stat-label">Approved</span>
        </div>
        <div className="stat locked">
          <span className="stat-value">{stats.locked}</span>
          <span className="stat-label">Locked</span>
        </div>
      </section>

      {/* Filters */}
      <section className="filters">
        <select value={filters.source_type} onChange={e => setFilters(f => ({ ...f, source_type: e.target.value }))}>
          <option value="">All Sources</option>
          <option value="SAP">SAP (Fuel/Procurement)</option>
          <option value="UTILITY">Utility (Electricity)</option>
          <option value="TRAVEL">Travel (Flights/Hotels)</option>
        </select>
        <select value={filters.status} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}>
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="FLAGGED">Flagged</option>
          <option value="APPROVED">Approved</option>
          <option value="LOCKED">Locked</option>
        </select>
        <select value={filters.scope} onChange={e => setFilters(f => ({ ...f, scope: e.target.value }))}>
          <option value="">All Scopes</option>
          <option value="SCOPE_1">Scope 1 (Direct)</option>
          <option value="SCOPE_2">Scope 2 (Energy)</option>
          <option value="SCOPE_3">Scope 3 (Value Chain)</option>
        </select>
      </section>

      {/* Records Table */}
      {loading ? (
        <p className="loading">Loading records...</p>
      ) : records.length === 0 ? (
        <p className="empty">No records found. Upload data above to get started.</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Scope</th>
                <th>Description</th>
                <th>Value</th>
                <th>Unit</th>
                <th>Status</th>
                <th>Flag Reason</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map(record => (
                <>
                  <tr key={record.id} className={`row-${record.status.toLowerCase()}`}>
                    <td><span className="source-tag">{record.source_type}</span></td>
                    <td>{record.scope?.replace('_', ' ')}</td>
                    <td className="desc-cell">{record.description || '—'}</td>
                    <td className="mono">{record.normalized_value}</td>
                    <td>{record.normalized_unit}</td>
                    <td><StatusBadge status={record.status} /></td>
                    <td className="flag-cell">{record.flag_reason || '—'}</td>
                    <td className="actions-cell">
                      {record.status === 'PENDING' && (
                        <>
                          <button className="btn-approve" onClick={() => handleApprove(record.id)}>✓ Approve</button>
                          <button className="btn-flag" onClick={() => handleFlag(record.id)}>⚑ Flag</button>
                        </>
                      )}
                      {record.status === 'FLAGGED' && (
                        <button className="btn-approve" onClick={() => handleApprove(record.id)}>✓ Approve</button>
                      )}
                      {record.status === 'APPROVED' && (
                        <button className="btn-lock" onClick={() => handleLock(record.id)}>🔒 Lock</button>
                      )}
                      {record.status === 'LOCKED' && (
                        <span className="locked-label">Audit-ready</span>
                      )}
                      <button className="btn-raw" onClick={() => setExpandedRow(expandedRow === record.id ? null : record.id)}>
                        {expandedRow === record.id ? '▲' : '▼'} Raw
                      </button>
                    </td>
                  </tr>
                  {expandedRow === record.id && (
                    <tr key={`${record.id}-raw`} className="raw-row">
                      <td colSpan="8">
                        <pre>{JSON.stringify(record.raw_data, null, 2)}</pre>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default App
