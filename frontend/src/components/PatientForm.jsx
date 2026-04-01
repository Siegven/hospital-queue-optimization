import { useState } from "react"

const initialState = {
  patient_id: "",
  age: "",
  heart_rate: "",
  systolic_blood_pressure: "",
  oxygen_saturation: "",
  body_temperature: "",
  pain_level: "",
  chronic_disease_count: "",
}

const FIELD_LIMITS = {
  age: { min: 0, max: 120 },
  heart_rate: { min: 30, max: 220 },
  systolic_blood_pressure: { min: 70, max: 250 },
  oxygen_saturation: { min: 50, max: 100 },
  body_temperature: { min: 30, max: 45 },
  pain_level: { min: 0, max: 10 },
  chronic_disease_count: { min: 0, max: 10 },
}

function PatientForm({ onAddPatient, submitting, clearError }) {
  const [formData, setFormData] = useState(initialState)
  const [formError, setFormError] = useState("")

  const validatePayload = (payload) => {
    for (const [fieldName, limits] of Object.entries(FIELD_LIMITS)) {
      const value = payload[fieldName]

      if (Number.isNaN(value)) {
        return `${fieldName.replaceAll("_", " ")} is invalid.`
      }

      if (value < limits.min || value > limits.max) {
        return `${fieldName.replaceAll("_", " ")} must be between ${limits.min} and ${limits.max}.`
      }
    }

    return ""
  }

  const handleChange = (event) => {
    const { name, value } = event.target
    setFormError("")
    clearError()

    setFormData((current) => ({
      ...current,
      [name]: name === "patient_id" ? value.toUpperCase() : value,
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    const payload = {
      ...formData,
      age: Number(formData.age),
      heart_rate: Number(formData.heart_rate),
      systolic_blood_pressure: Number(formData.systolic_blood_pressure),
      oxygen_saturation: Number(formData.oxygen_saturation),
      body_temperature: Number(formData.body_temperature),
      pain_level: Number(formData.pain_level),
      chronic_disease_count: Number(formData.chronic_disease_count),
      previous_er_visits: 0,
      arrival_mode: "walk_in",
    }

    const validationError = validatePayload(payload)
    if (validationError) {
      setFormError(`Invalid entry: ${validationError}`)
      return
    }

    const added = await onAddPatient(payload)
    if (added) {
      setFormError("")
      setFormData(initialState)
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow subtle">Patient Intake</p>
          <h2>Add incoming patient</h2>
        </div>
      </div>

      {formError ? <div className="form-alert">{formError}</div> : null}

      <form className="patient-form" onSubmit={handleSubmit}>
        <label>
          Patient ID
          <input
            name="patient_id"
            value={formData.patient_id}
            onChange={handleChange}
            placeholder="PAT-1007"
            style={{ textTransform: "uppercase" }}
            required
          />
        </label>

        <label>
          Age
          <input name="age" type="number" min="0" max="120" step="0.1" value={formData.age} onChange={handleChange} required />
        </label>

        <label>
          Heart Rate
          <input name="heart_rate" type="number" min="30" max="220" step="0.1" value={formData.heart_rate} onChange={handleChange} required />
        </label>

        <label>
          Systolic BP (mmHg)
          <input
            name="systolic_blood_pressure"
            type="number"
            min="70"
            max="250"
            step="0.1"
            value={formData.systolic_blood_pressure}
            onChange={handleChange}
            required
          />
        </label>

        <label>
          Oxygen Saturation (%)
          <input
            name="oxygen_saturation"
            type="number"
            min="50"
            max="100"
            step="0.1"
            value={formData.oxygen_saturation}
            onChange={handleChange}
            required
          />
        </label>

        <label>
          Body Temperature (Celsius)
          <input
            name="body_temperature"
            type="number"
            min="30"
            max="45"
            step="0.01"
            value={formData.body_temperature}
            onChange={handleChange}
            required
          />
        </label>

        <label>
          Pain Level
          <input name="pain_level" type="number" min="0" max="10" value={formData.pain_level} onChange={handleChange} required />
        </label>

        <label>
          Chronic Disease Count
          <input
            name="chronic_disease_count"
            type="number"
            min="0"
            max="10"
            value={formData.chronic_disease_count}
            onChange={handleChange}
            required
          />
        </label>

        <button className="secondary-button" type="submit" disabled={submitting}>
          {submitting ? "Adding..." : "Add Patient"}
        </button>
      </form>
    </section>
  )
}

export default PatientForm
