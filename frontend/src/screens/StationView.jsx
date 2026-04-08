import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { enterStation } from '../api/client';
import useGameStore from '../store/gameSlice';
import styles from './StationView.module.css';

const STATION_CONTENT = {
  sample_prep: {
    title: 'Sample Preparation',
    description:
      'Prepare the infected and control samples for mass spectrometry. Open cells, isolate proteins, reduce disulfide bonds, alkylate, and digest with trypsin.',
    objective: 'Complete the preparation workflow before moving to the mass spectrometer.',
  },
  mass_spec: {
    title: 'Mass Spectrometer',
    description:
      'Run the samples on the mass spectrometer and choose an acquisition method.',
    objective: 'Choose between DDA and DIA and start the acquisition.',
  },
  spectral_search: {
    title: 'Spectral Search Station',
    description: 'Identify peptides by matching spectra against a protein sequence database.',
    objective: 'Set search constraints and run peptide-spectrum matching.',
  },
  filtering: {
    title: 'Filtering Station',
    description: 'Filter identifications to remove low-confidence or contaminant entries.',
    objective: 'Apply quality thresholds and keep only robust identifications.',
  },
  transform: {
    title: 'Transform Station',
    description: 'Transform intensity values to stabilize variance before comparison.',
    objective: 'Choose a transformation and prepare values for downstream modeling.',
  },
  normalize: {
    title: 'Normalize Station',
    description: 'Correct systematic intensity shifts between samples.',
    objective: 'Apply normalization to improve cross-sample comparability.',
  },
  imputer: {
    title: 'Imputer Station',
    description: 'Handle missing values introduced by low abundance and stochastic sampling.',
    objective: 'Select a missing-value strategy and impute the matrix.',
  },
  multiple_testing_corrector: {
    title: 'Multiple Testing Corrector',
    description: 'Control false discoveries after running many statistical tests.',
    objective: 'Apply correction and choose a threshold for significance calls.',
  },
  the_cutter: {
    title: 'The Cutter',
    description: 'Set fold-change and confidence cutoffs to define your final candidate list.',
    objective: 'Cut the result space to a biologically interpretable shortlist.',
  },
  statistical_analysis: {
    title: 'Statistical Analysis',
    description:
      'Compare conditions and identify significantly regulated proteins and pathways.',
    objective: 'Run the analysis and summarize the most relevant biological signals.',
  },
  veit: {
    title: 'Veit',
    description:
      'Veit can guide you based on your progress and receive your final report.',
    objective: 'Hand in your report when you are ready.',
  },
};

const FALLBACK_CONTENT = {
  title: 'Unknown Station',
  description: 'No station information was found.',
  objective: 'Return to the map.',
};

export default function StationView() {
  const { stationId } = useParams();
  const navigate = useNavigate();
  const { sessionId } = useGameStore();

  const [stationData, setStationData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const content = STATION_CONTENT[stationId] ?? FALLBACK_CONTENT;

  useEffect(() => {
    if (!stationId) return;

    setLoading(true);
    setError('');

    enterStation(stationId, sessionId)
      .then((res) => setStationData(res.data))
      .catch(() => {
        // Backend enter endpoint not yet implemented — use placeholder data
        setStationData({
          message: `Entered station '${stationId}' successfully.`,
          station_id: stationId,
        });
      })
      .finally(() => setLoading(false));
  }, [stationId, sessionId]);

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>{content.title}</h1>
        <p className={styles.text}>{content.description}</p>

        <div className={styles.box}>
          <strong>Objective:</strong>
          <p className={styles.boxText}>{content.objective}</p>
        </div>

        {loading && <p className={styles.info}>Loading station…</p>}
        {error && <p className={styles.error}>{error}</p>}

        {stationData && !loading && (
          <div className={styles.box}>
            <strong>Status:</strong>
            <p className={styles.boxText}>{stationData.message}</p>
          </div>
        )}

        <div className={styles.buttonRow}>
          <button className={styles.secondaryButton} onClick={() => navigate('/world')}>
            Back to map
          </button>
          <button
            className={styles.primaryButton}
            onClick={() => navigate(`/station/${stationId}/params`)}
            disabled={loading}
          >
            Configure &amp; Run →
          </button>
        </div>
      </div>
    </div>
  );
}
