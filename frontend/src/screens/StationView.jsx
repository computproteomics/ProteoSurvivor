import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { enterStation } from '../api/client';
import useGameStore from '../store/gameSlice';
import { getStationDescription, getStationTitle } from '../assets/stationConfig';
import styles from './StationView.module.css';

export default function StationView() {
  const { stationId } = useParams();
  const navigate = useNavigate();
  const { sessionId } = useGameStore();

  const [stationData, setStationData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const content = {
    title: getStationTitle(stationId),
    description: getStationDescription(stationId),
    objective: 'Configure and run this station before returning to the map.',
  };

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
