import { useParams, useNavigate } from 'react-router-dom';
import useGameStore from '../store/gameSlice';
import { getStationTitle } from '../assets/stationConfig';
import { getStationResultsRenderer } from './resultRenderer';
import styles from './StationResults.module.css';

export default function StationResults() {
  // Read the current station from the route.
  const { stationId } = useParams();
  const navigate = useNavigate();
  // Pull the latest station output and completion action from shared state.
  const { stationResults, markStationComplete } = useGameStore();

  const title = getStationTitle(stationId);

  function handleBackToMap() {
    // Mark the station done before returning to the map.
    markStationComplete(stationId);
    navigate('/world');
  }

  function handleRetry() {
    // Let the user adjust the same station parameters again.
    navigate(`/station/${stationId}/params`);
  }

  if (!stationResults) {
    return (
      <div className={styles.page}>
        <div className={styles.card}>
          <h1 className={styles.title}>No Results</h1>
          <p className={styles.text}>No results are available for this station yet.</p>
          <button className={styles.primaryButton} onClick={() => navigate(`/station/${stationId}`)}>
            Back to station
          </button>
        </div>
      </div>
    );
  }

  if (stationResults.blocked) {
    return (
      <div className={styles.page}>
        <div className={styles.card}>
          <h1 className={styles.title}>Station Locked</h1>
          <p className={styles.text}>
            {stationResults.feedback || 'You need to complete a previous station before accessing this one.'}
          </p>

          <div className={styles.buttonRow}>
            <button className={styles.primaryButton} onClick={() => navigate('/world')}>
              Back to map
            </button>
          </div>
        </div>
      </div>
    );
  }

  const StationResultContent = getStationResultsRenderer(stationId);

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.headerRow}>
          <span className={styles.stationBadge}>{title}</span>
          <span className={styles.completeBadge}>✅ Run complete</span>
        </div>

        <h1 className={styles.title}>Results</h1>
        <StationResultContent stationResults={stationResults} />

        <div className={styles.buttonRow}>
          <button className={styles.secondaryButton} onClick={handleRetry}>
            ← Adjust parameters
          </button>
          <button className={styles.primaryButton} onClick={handleBackToMap}>
            Back to map ✓
          </button>
        </div>
      </div>
    </div>
  );
}
