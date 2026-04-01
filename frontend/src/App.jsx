import { useEffect, useState } from "react"
import PatientForm from "./components/PatientForm"
import QueueTable from "./components/QueueTable"

const API_BASE = "http://127.0.0.1:5000"

function App() {
  const [patients, setPatients] = useState([])
  const [resolvedPatients, setResolvedPatients] = useState([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState("")
  const [theme, setTheme] = useState("light")

  const loadPatients = async () => {
    try {
      const response = await fetch(`${API_BASE}/patients`)
      const data = await response.json()
      setPatients(data.active ?? [])
      setResolvedPatients(data.resolved ?? [])
    } catch (loadError) {
      setError("Unable to load patients from the queue.")
    }
  }

  useEffect(() => {
    loadPatients()
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
  }, [theme])

  const handleAddPatient = async (formData) => {
    setSubmitting(true)
    setError("")

    try {
      const response = await fetch(`${API_BASE}/add_patient`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.error || "Failed to add patient.")
      }

      await loadPatients()
      return true
    } catch (submitError) {
      setError(submitError.message)
      return false
    } finally {
      setSubmitting(false)
    }
  }

  const handleOptimize = async () => {
    setLoading(true)
    setError("")

    try {
      const response = await fetch(`${API_BASE}/optimize_queue`, {
        method: "POST",
      })

      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.error || "Failed to optimize queue.")
      }

      const data = await response.json()
      setPatients(data)
    } catch (optimizeError) {
      setError(optimizeError.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAdmitPatient = async (patientId) => {
    setError("")

    try {
      const response = await fetch(`${API_BASE}/patients/${patientId}/resolve`, {
        method: "POST",
      })

      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.error || "Failed to admit patient.")
      }

      await loadPatients()
    } catch (admitError) {
      setError(admitError.message)
    }
  }

  const handleDeletePatient = async (patientId) => {
    setError("")

    try {
      const response = await fetch(`${API_BASE}/patients/${patientId}`, {
        method: "DELETE",
      })

      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.error || "Failed to delete patient.")
      }

      await loadPatients()
    } catch (deleteError) {
      setError(deleteError.message)
    }
  }

  return (
    <div className="dashboard-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow subtle">Emergency Command Center</p>
          <h1>Hospital Queue Dashboard</h1>
        </div>

        <div className="topbar-status">
          <button
            className="theme-toggle"
            type="button"
            onClick={() => setTheme((currentTheme) => (currentTheme === "light" ? "dark" : "light"))}
          >
            {theme === "light" ? "Dark Mode" : "Light Mode"}
          </button>
          <div className="status-pill">
            <span className="status-dot" />
            Queue Live
          </div>
          <div className="queue-count">{patients.length} patients waiting</div>
        </div>
      </header>

      {error ? <div className="top-alert">{error}</div> : null}

      <section className="workspace-grid">
        <PatientForm
          onAddPatient={handleAddPatient}
          submitting={submitting}
          clearError={() => setError("")}
        />

        <section className="panel queue-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow subtle">Live Queue</p>
              <h2>Emergency queue monitor</h2>
            </div>
            <button className="primary-button" onClick={handleOptimize} disabled={loading || !patients.length}>
              {loading ? "Optimizing..." : "Optimize Queue"}
            </button>
          </div>

          <QueueTable
            title="Active Queue"
            patients={patients}
            emptyText="No patients added yet."
            showActions
            onAdmitPatient={handleAdmitPatient}
            onDeletePatient={handleDeletePatient}
          />

          <QueueTable
            title="Resolved / Admitted"
            patients={resolvedPatients}
            emptyText="No resolved patients yet."
            onDeletePatient={handleDeletePatient}
          />
        </section>
      </section>
    </div>
  )
}

export default App
