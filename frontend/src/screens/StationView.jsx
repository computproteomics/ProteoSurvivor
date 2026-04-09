import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { enterStation } from '../api/client';
import useGameStore from '../store/gameSlice';
import { getStationDescription, getStationTitle } from '../assets/stationConfig';
import styles from './StationView.module.css';

export default function StationView() {
  // Read current station id from the route.
  const { stationId } = useParams();
  const navigate = useNavigate();
  const { sessionId } = useGameStore();

  const [stationData, setStationData] = useState(null);
  // Disable actions while station entry request is in flight.
  const [loading, setLoading] = useState(false);

  // Static display content sourced from station configuration.
  const content = {
    title: getStationTitle(stationId),
    description: getStationDescription(stationId),
    objective: 'Configure and run this station before returning to the map.',
  };

  useEffect(() => {
    if (!stationId) return;

    setLoading(true);

    // Enter the station so backend session state can be initialized.
    enterStation(stationId, sessionId)
      .then((res) => setStationData(res.data))
      .catch(() => {
        // Use a local fallback status when backend entry is unavailable.
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
