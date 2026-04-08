import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { runStation } from '../api/client';
import useGameStore from '../store/gameSlice';
import styles from './ParametrizationView.module.css';

// ─── Per-station parameter schemas ──────────────────────────────────────────

const PARAM_SCHEMAS = {
  sample_prep: [
    {
      id: 'lysis_method',
      label: 'Lysis Method',
      type: 'select',
      options: ['mechanical', 'chemical', 'enzymatic'],
      defaultValue: 'chemical',
    },
    {
      id: 'enzyme',
      label: 'Digestion Enzyme',
      type: 'select',
      options: ['trypsin', 'lys-c', 'asp-n', 'glu-c'],
      defaultValue: 'trypsin',
    },
    {
      id: 'reduction_agent',
      label: 'Reduction Agent',
      type: 'select',
      options: ['DTT', 'TCEP', 'β-ME'],
      defaultValue: 'DTT',
    },
    {
      id: 'alkylation_agent',
      label: 'Alkylation Agent',
      type: 'select',
      options: ['iodoacetamide', 'acrylamide'],
      defaultValue: 'iodoacetamide',
    },
  ],

  mass_spec: [
    {
      id: 'acquisition_mode',
      label: 'Acquisition Mode',
      type: 'select',
      options: ['DDA', 'DIA'],
      defaultValue: 'DDA',
    },
    {
      id: 'gradient_length_min',
      label: 'Gradient Length (min)',
      type: 'number',
      min: 30,
      max: 180,
      step: 5,
      defaultValue: 60,
    },
    {
      id: 'ms1_resolution',
      label: 'MS1 Resolution',
      type: 'select',
      options: ['60000', '120000', '240000'],
      defaultValue: '120000',
    },
    {
      id: 'ms2_resolution',
      label: 'MS2 Resolution',
      type: 'select',
      options: ['15000', '30000', '60000'],
      defaultValue: '30000',
    },
  ],

  spectral_search: [
    {
      id: 'database',
      label: 'Protein Database',
      type: 'select',
      options: ['SwissProt', 'TrEMBL', 'RefSeq'],
      defaultValue: 'SwissProt',
    },
    {
      id: 'enzyme',
      label: 'Enzyme',
      type: 'select',
      options: ['trypsin', 'lys-c', 'asp-n'],
      defaultValue: 'trypsin',
    },
    {
      id: 'missed_cleavages',
      label: 'Missed Cleavages',
      type: 'number',
      min: 0,
      max: 4,
      step: 1,
      defaultValue: 2,
    },
    {
      id: 'min_peptide_length',
      label: 'Min Peptide Length',
      type: 'number',
      min: 4,
      max: 10,
      step: 1,
      defaultValue: 7,
    },
    {
      id: 'max_peptide_length',
      label: 'Max Peptide Length',
      type: 'number',
      min: 20,
      max: 60,
      step: 1,
      defaultValue: 35,
    },
    {
      id: 'fdr_threshold',
      label: 'FDR Threshold',
      type: 'select',
      options: ['0.01', '0.05'],
      defaultValue: '0.01',
    },
  ],

  statistical_analysis: [
    {
      id: 'normalization',
      label: 'Normalisation Method',
      type: 'select',
      options: ['none', 'median', 'quantile'],
      defaultValue: 'median',
    },
    {
      id: 'statistical_test',
      label: 'Statistical Test',
      type: 'select',
      options: ['t-test', 'limma', 'DESeq2'],
      defaultValue: 'limma',
    },
    {
      id: 'fdr_threshold',
      label: 'FDR Threshold',
      type: 'select',
      options: ['0.01', '0.05'],
      defaultValue: '0.05',
    },
    {
      id: 'fold_change_threshold',
      label: 'Fold-change Threshold',
      type: 'select',
      options: ['1.5', '2.0', '3.0'],
      defaultValue: '1.5',
    },
  ],

  filtering: [
    {
      id: 'min_confidence_score',
      label: 'Minimum Confidence Score',
      type: 'number',
      min: 0,
      max: 100,
      step: 1,
      defaultValue: 70,
    },
    {
      id: 'remove_contaminants',
      label: 'Remove Contaminants',
      type: 'select',
      options: ['yes', 'no'],
      defaultValue: 'yes',
    },
  ],

  transform: [
    {
      id: 'transform_method',
      label: 'Transform Method',
      type: 'select',
      options: ['log2', 'log10', 'none'],
      defaultValue: 'log2',
    },
  ],

  normalize: [
    {
      id: 'normalization',
      label: 'Normalisation Method',
      type: 'select',
      options: ['median', 'quantile', 'none'],
      defaultValue: 'median',
    },
  ],

  imputer: [
    {
      id: 'imputation_method',
      label: 'Imputation Method',
      type: 'select',
      options: ['knn', 'minprob', 'zero_fill'],
      defaultValue: 'knn',
    },
  ],

  multiple_testing_corrector: [
    {
      id: 'correction_method',
      label: 'Correction Method',
      type: 'select',
      options: ['Benjamini-Hochberg', 'Bonferroni', 'Holm'],
      defaultValue: 'Benjamini-Hochberg',
    },
    {
      id: 'alpha',
      label: 'Significance Alpha',
      type: 'select',
      options: ['0.01', '0.05', '0.10'],
      defaultValue: '0.05',
    },
  ],

  the_cutter: [
    {
      id: 'fold_change_threshold',
      label: 'Fold-change Threshold',
      type: 'select',
      options: ['1.5', '2.0', '3.0'],
      defaultValue: '2.0',
    },
    {
      id: 'keep_top_n',
      label: 'Keep Top N Hits',
      type: 'number',
      min: 10,
      max: 500,
      step: 10,
      defaultValue: 100,
    },
  ],

  veit: [
    {
      id: 'report_text',
      label: 'Your Report',
      type: 'textarea',
      placeholder:
        'Summarise your findings: which proteins were regulated, what pathways were affected, and what conclusions you can draw…',
      defaultValue: '',
    },
  ],
};

const STATION_TITLES = {
  sample_prep: 'Sample Preparation',
  mass_spec: 'Mass Spectrometer',
  spectral_search: 'Spectral Search Station',
  filtering: 'Filtering Station',
  transform: 'Transform Station',
  normalize: 'Normalize Station',
  imputer: 'Imputer Station',
  multiple_testing_corrector: 'Multiple Testing Corrector',
  the_cutter: 'The Cutter',
  statistical_analysis: 'Statistical Analysis',
  veit: 'Veit',
};

// ─── Build default form values from schema ───────────────────────────────────

function buildDefaults(schema) {
  return Object.fromEntries(schema.map((f) => [f.id, f.defaultValue]));
}

// ─── Single field renderer ───────────────────────────────────────────────────

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
          {field.options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
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

// ─── Main component ──────────────────────────────────────────────────────────

export default function ParametrizationView() {
  const { stationId } = useParams();
  const navigate = useNavigate();
  const { setStationParams, setStationResults } = useGameStore();

  const schema = PARAM_SCHEMAS[stationId] ?? [];
  const title = STATION_TITLES[stationId] ?? 'Station';

  const [values, setValues] = useState(buildDefaults(schema));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function handleChange(fieldId, newValue) {
    setValues((prev) => ({ ...prev, [fieldId]: newValue }));
  }

  async function handleRun() {
    setLoading(true);
    setError('');
    setStationParams(stationId, values);

    try {
      const res = await runStation(stationId, values);
      setStationResults(res.data.results ?? res.data);
      navigate(`/station/${stationId}/results`);
    } catch (err) {
      // If the backend isn't running, fall back to a client-side placeholder
      // so the UI flow can still be demonstrated
      setStationResults({
        summary: `Parameters recorded for ${title}. (Backend not reachable — showing offline results.)`,
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
          <p className={styles.subtitle}>Set the parameters then click <em>Run</em> to send them to the lab.</p>
        </div>

        {schema.length === 0 ? (
          <p className={styles.noParams}>No configurable parameters for this station.</p>
        ) : (
          <form className={styles.form} onSubmit={(e) => { e.preventDefault(); handleRun(); }}>
            {schema.map((field) => (
              <ParamField
                key={field.id}
                field={field}
                value={values[field.id]}
                onChange={handleChange}
              />
            ))}

            {error && <p className={styles.error}>{error}</p>}

            <div className={styles.buttonRow}>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => navigate(`/station/${stationId}`)}
                disabled={loading}
              >
                ← Back
              </button>
              <button
                type="submit"
                className={styles.primaryButton}
                disabled={loading}
              >
                {loading ? 'Running…' : 'Run Station →'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
