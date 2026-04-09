import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { runStation } from '../api/client';
import useGameStore from '../store/gameSlice';
import { getStationParameters, getStationTitle } from '../assets/stationConfig';
import styles from './ParametrizationView.module.css';

function buildDefaults(schema) {
  return Object.fromEntries(schema.map((field) => [field.id, field.defaultValue]));
}

function getOptionLabel(field, option) {
  return field.optionLabels?.[option] ?? option;
}

function ParamField({ field, value, onChange }) {
  if (field.type === 'select') {
    return (
      <div className={styles.field}>
        <label className={styles.label} htmlFor={field.id}>
          {field.label}
        </label>
        <select
          id={field.id}
          className={styles.input}
          value={value}
          onChange={(e) => onChange(field.id, e.target.value)}
        >
          {field.options.map((option) => (
            <option key={option} value={option}>
              {getOptionLabel(field, option)}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (field.type === 'number') {
    return (
      <div className={styles.field}>
        <label className={styles.label} htmlFor={field.id}>
          {field.label}
        </label>
        <input
          id={field.id}
          className={styles.input}
          type="number"
          min={field.min}
          max={field.max}
          step={field.step}
          value={value}
          onChange={(e) => onChange(field.id, e.target.value)}
        />
      </div>
    );
  }

  if (field.type === 'slider') {
    return (
      <div className={styles.field}>
        <label className={styles.label} htmlFor={field.id}>
          {field.label}: {value}
        </label>
        <input
          id={field.id}
          className={styles.input}
          type="range"
          min={field.min}
          max={field.max}
          step={field.step}
          value={value}
          onChange={(e) => onChange(field.id, e.target.value)}
        />
      </div>
    );
  }

  if (field.type === 'textarea') {
    return (
      <div className={styles.field}>
        <label className={styles.label} htmlFor={field.id}>
          {field.label}
        </label>
        <textarea
          id={field.id}
          className={styles.textarea}
          rows={8}
          placeholder={field.placeholder}
          value={value}
          onChange={(e) => onChange(field.id, e.target.value)}
        />
      </div>
    );
  }

  return null;
}

export default function ParametrizationView() {
  const { stationId } = useParams();
  const navigate = useNavigate();
  const { setStationParams, setStationResults } = useGameStore();

  const schema = getStationParameters(stationId);
  const title = getStationTitle(stationId);

  const [values, setValues] = useState(buildDefaults(schema));
  const [loading, setLoading] = useState(false);

  function handleChange(fieldId, newValue) {
    setValues((prev) => ({ ...prev, [fieldId]: newValue }));
  }

  async function handleRun() {
    setLoading(true);
    setStationParams(stationId, values);

    try {
      const res = await runStation(stationId, values);
      setStationResults(res.data.results ?? res.data);
      navigate(`/station/${stationId}/results`);
    } catch (err) {
      setStationResults({
        summary: `Parameters recorded for ${title}. (Backend not reachable - showing offline results.)`,
        params_received: values,
      });
      navigate(`/station/${stationId}/results`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.subtitle}>
            Set the parameters then click <em>Run</em> to send them to the lab.
          </p>
        </div>

        {schema.length === 0 ? (
          <p className={styles.noParams}>No configurable parameters for this station.</p>
        ) : (
          <form
            className={styles.form}
            onSubmit={(e) => {
              e.preventDefault();
              handleRun();
            }}
          >
            {schema.map((field) => (
              <ParamField
                key={field.id}
                field={field}
                value={values[field.id]}
                onChange={handleChange}
              />
            ))}

            <div className={styles.buttonRow}>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => navigate(`/station/${stationId}`)}
                disabled={loading}
              >
                Back
              </button>
              <button type="submit" className={styles.primaryButton} disabled={loading}>
                {loading ? 'Running...' : 'Run Station'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
