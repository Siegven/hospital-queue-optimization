function formatNumber(value) {
  if (value === null || value === undefined) {
    return "--"
  }
  return Number(value).toString()
}

function QueueTable({ title, patients, emptyText, showActions = false, onAdmitPatient, onDeletePatient }) {
  return (
    <section className="queue-block">
      <div className="queue-block-head">
        <h3>{title}</h3>
        <span>{patients.length} patients</span>
      </div>

      <div className="table-wrap">
        <table className="queue-table">
          <thead>
            <tr>
              <th>Patient ID</th>
              <th>Age</th>
              <th>HR</th>
              <th>BP</th>
              <th>Oxygen</th>
              <th>Temp (C)</th>
              <th>Pain</th>
              <th>Priority</th>
              <th>Anomaly Score</th>
              <th>Priority Score</th>
              <th>Status</th>
              {showActions ? <th>Actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {patients.length === 0 ? (
              <tr>
                <td colSpan={showActions ? 12 : 11} className="empty-row">
                  {emptyText}
                </td>
              </tr>
            ) : (
              patients.map((patient) => (
                <tr
                  key={`${patient.patient_id}-${patient.status ?? "waiting"}`}
                  className={`priority-row ${(patient.priority_label || "low").toLowerCase()}`}
                >
                  <td>{patient.patient_id}</td>
                  <td>{formatNumber(patient.age)}</td>
                  <td>{formatNumber(patient.heart_rate)}</td>
                  <td>{formatNumber(patient.systolic_blood_pressure)}</td>
                  <td>{formatNumber(patient.oxygen_saturation)}</td>
                  <td>{formatNumber(patient.body_temperature)}</td>
                  <td>{formatNumber(patient.pain_level)}</td>
                  <td>
                    {patient.priority_label ? (
                      <span className={`priority-badge ${patient.priority_label.toLowerCase()}`}>
                        {patient.priority_label}
                      </span>
                    ) : (
                      "--"
                    )}
                  </td>
                  <td>{formatNumber(patient.anomaly_score)}</td>
                  <td>
                    <strong>{formatNumber(patient.priority_score)}</strong>
                  </td>
                  <td>
                    <span className={`status-badge ${(patient.status || "waiting").toLowerCase()}`}>
                      {patient.status || "Waiting"}
                    </span>
                  </td>
                  {showActions ? (
                    <td>
                      <div className="row-actions">
                        <button
                          className="table-action admit"
                          type="button"
                          onClick={() => onAdmitPatient(patient.patient_id)}
                        >
                          Admit
                        </button>
                        <button
                          className="table-action delete"
                          type="button"
                          onClick={() => onDeletePatient(patient.patient_id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  ) : null}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default QueueTable
