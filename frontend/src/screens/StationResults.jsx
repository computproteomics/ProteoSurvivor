import { useParams, useNavigate } from 'react-router-dom';
import useGameStore from '../store/gameSlice';
import { getStationTitle } from '../assets/stationConfig';
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

  const { summary, recommendation, ...detailFields } = stationResults;

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.headerRow}>
          <span className={styles.stationBadge}>{title}</span>
          <span className={styles.completeBadge}>✅ Run complete</span>
        </div>

        <h1 className={styles.title}>Results</h1>

        {summary && (
          <div className={styles.summaryBox}>
            {/* Short summary shown above the raw result fields. */}
            <p className={styles.summaryText}>{summary}</p>
          </div>
        )}

        {Object.keys(detailFields).length > 0 && (
          <table className={styles.table}>
            <tbody>
              {/* Render every remaining field as a simple key/value row. */}
              {Object.entries(detailFields).map(([key, value]) => (
                <tr key={key} className={styles.row}>
                  <td className={styles.key}>{formatKey(key)}</td>
                  <td className={styles.value}>{formatValue(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {recommendation && (
          <div className={styles.recommendationBox}>
            <strong>💡 Recommendation:</strong>
            <p className={styles.recommendationText}>{recommendation}</p>
          </div>
        )}

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

function formatKey(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(value) {
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'object' && value !== null) return JSON.stringify(value);
  return String(value);
}
