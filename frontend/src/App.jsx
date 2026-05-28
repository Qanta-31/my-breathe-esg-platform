import { useState, useEffect } from 'react'
import axios from 'axios'

function App() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)

  // 1. Fetch the data from your Django backend
  const fetchRecords = () => {
    axios.get('https://breathe-esg-platform-oe2e.onrender.com/api/records/')
      .then(response => {
        setRecords(response.data)
        setLoading(false)
      })
      .catch(error => {
        console.error("Error fetching data:", error)
        setLoading(false)
      })
  }

  // Run the fetch as soon as the page loads
  useEffect(() => {
    fetchRecords()
  }, [])

  // 2. The Approval Engine (Updates the database)
  const handleApprove = (id) => {
    // We send a PATCH request to change the status to APPROVED and mark it as edited by an analyst
    axios.patch(`https://breathe-esg-platform-oe2e.onrender.com/api/records/${id}/`, {
      status: 'APPROVED', 
      is_edited: true 
    })
      .then(() => fetchRecords()) // Refresh the table after approving
      .catch(err => console.error(err))
  }

  if (loading) return <h2 style={{ padding: '20px' }}>Loading Analyst Dashboard...</h2>

  return (
    <div style={{ padding: '40px', fontFamily: 'sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ borderBottom: '2px solid #333', paddingBottom: '10px' }}>
        Breathe ESG - Analyst Review Dashboard
      </h1>
      
      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', marginTop: '20px' }}>
        <thead>
          <tr style={{ backgroundColor: '#f4f4f4', borderBottom: '2px solid #ddd' }}>
            <th style={{ padding: '12px' }}>Company</th>
            <th>Source</th>
            <th>Scope</th>
            <th>Normalized Value</th>
            <th>Unit</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {records.map(record => (
            <tr key={record.id} style={{ borderBottom: '1px solid #ddd' }}>
              <td style={{ padding: '12px' }}>{record.tenant_name}</td>
              <td><strong>{record.source_type}</strong></td>
              <td>{record.scope}</td>
              <td style={{ fontFamily: 'monospace', fontSize: '1.1em' }}>{record.normalized_value}</td>
              <td>{record.normalized_unit}</td>
              <td>
                <span style={{
                  padding: '6px 10px', 
                  borderRadius: '12px',
                  fontSize: '0.85em',
                  fontWeight: 'bold',
                  backgroundColor: record.status === 'FLAGGED' ? '#ffebee' : record.status === 'APPROVED' ? '#e8f5e9' : '#fff3e0',
                  color: record.status === 'FLAGGED' ? '#c62828' : record.status === 'APPROVED' ? '#2e7d32' : '#ef6c00'
                }}>
                  {record.status}
                </span>
              </td>
              <td>
                {record.status !== 'APPROVED' && (
                  <button 
                    onClick={() => handleApprove(record.id)} 
                    style={{ 
                      padding: '8px 16px', 
                      cursor: 'pointer', 
                      backgroundColor: '#2e7d32', 
                      color: 'white', 
                      border: 'none', 
                      borderRadius: '4px' 
                    }}>
                    Approve
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default App