import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { runStation } from '../api/client';
import useGameStore from '../store/gameSlice';
import {
  getStationBackgroundImage,
  getStationParameters,
  getStationTitle,
} from '../assets/stationConfig';
import styles from './ParametrizationView.module.css';

function buildDefaults(schema) {
  return Object.fromEntries(schema.map((field) => [field.id, field.defaultValue]));
}

function getOptionLabel(field, option) {
  return field.optionLabels?.[option] ?? option;
}

function ParameterLabel({ field, value }) {
  const labelText = field.type === 'slider' ? `${field.label}: ${value}` : field.label;

  return (
    <label className={styles.label} htmlFor={field.id}>
      <span>{labelText}</span>
      {field.tooltip ? (
        <span
          className={styles.tooltipIcon}
          title={field.tooltip}
          aria-label={`Info: ${field.tooltip}`}
        >
          ?
        </span>
      ) : null}
    </label>
  );
}

function ParamField({ field, value, onChange }) {
  if (field.type === 'select') {
    return (
      <div className={styles.field}>
        <ParameterLabel field={field} value={value} />
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
        <ParameterLabel field={field} value={value} />
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
        <ParameterLabel field={field} value={value} />
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
        <ParameterLabel field={field} value={value} />
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

function getRunFailureResult(title, values, err) {
  const feedback =
    err?.response?.data?.feedback ||
    err?.response?.data?.detail ||
    err?.message ||
    'The station run failed before results could be displayed.';

  return {
    success: false,
    summary: `Could not display results for ${title}.`,
    feedback,
    params_received: values,
  };
}

export default function ParametrizationView() {
  const { stationId } = useParams();
  const navigate = useNavigate();
  const { setStationParams, setStationResults } = useGameStore();

  const schema = getStationParameters(stationId);
  const title = getStationTitle(stationId);
  const stationBackground = getStationBackgroundImage(stationId);
  const pageStyle = stationBackground
    ? {
      backgroundImage: `linear-gradient(rgba(15, 23, 42, 0.5), rgba(15, 23, 42, 0.5)), url(${stationBackground})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
    }
    : undefined;

  const [values, setValues] = useState(buildDefaults(schema));
  const [loading, setLoading] = useState(false);

  function handleChange(fieldId, newValue) {
    setValues((prev) => ({ ...prev, [fieldId]: newValue }));
  }

  async function handleRun() {
    setLoading(true);
    setStationParams(stationId, values);

    let resultPayload;
    let runSuccess;

    try {
      const res = await runStation(stationId, values);
      const responseData = res.data ?? {};
      resultPayload = responseData.results ?? responseData;
      runSuccess = responseData.success ?? resultPayload.success;
    } catch (err) {
      setStationResults(getRunFailureResult(title, values, err));
      navigate(`/station/${stationId}/results`);
      return;
    }

    try {
      setStationResults({
        ...resultPayload,
        success: runSuccess,
      });
      navigate(`/station/${stationId}/results`);
    } catch (err) {
      setStationResults(getRunFailureResult(title, values, err));
      navigate(`/station/${stationId}/results`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.page} style={pageStyle}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.subtitle}>
            Set the parameters then click <em>Run</em> to send them to the lab.
          </p>
        </div>

        {schema.length === 0 ? (
          <>
            <p className={styles.noParams}>No configurable parameters for this station.</p>

            <div className={styles.buttonRow}>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => navigate(`/station/${stationId}`)}
                disabled={loading}
              >
                Back
              </button>

              <button
                type="button"
                className={styles.primaryButton}
                onClick={handleRun}
                disabled={loading}
              >
                {loading ? 'Running...' : 'Run Station'}
              </button>
            </div>
          </>
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
