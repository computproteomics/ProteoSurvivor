import styles from './StationResults.module.css';

export function getStationResultsRenderer(stationId) {
  if (stationId === 'transform') {
    return TransformStationResultsContent;
  }
  return GenericStationResultsContent;
}

function GenericStationResultsContent({ stationResults }) {
  const { summary, recommendation, ...detailFields } = stationResults;

  return (
    <>
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
    </>
  );
}

function TransformStationResultsContent({ stationResults }) {
  const wasSuccessful = stationResults.success ?? stationResults.succes;
  const feedback = stationResults.feedback;
  const transformImages = normalizeImageList(stationResults.img);

  return (
    <>
      <div className={wasSuccessful ? styles.summaryBox : styles.errorBox}>
        <p className={wasSuccessful ? styles.summaryText : styles.errorText}>
          {wasSuccessful
            ? 'Station successfully completed.'
            : 'Station run did not complete successfully.'}
        </p>
      </div>

      {feedback && (
        <div className={styles.recommendationBox}>
          <strong>Feedback</strong>
          <p className={styles.recommendationText}>{feedback}</p>
        </div>
      )}

      {wasSuccessful && transformImages.length > 0 && (
        <div className={styles.imageSection}>
          <h2 className={styles.imageTitle}>Transformation Plots</h2>
          <div className={styles.imageGrid}>
            {transformImages.map((imageSrc, index) => (
              <figure key={index} className={styles.imageCard}>
                <img
                  src={toImageDataUrl(imageSrc)}
                  alt={`Transformation plot ${index + 1}`}
                  className={styles.resultImage}
                />
              </figure>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function normalizeImageList(imgValue) {
  if (Array.isArray(imgValue)) {
    return imgValue.filter((value) => typeof value === 'string' && value.trim().length > 0);
  }
  if (typeof imgValue === 'string' && imgValue.trim().length > 0) {
    return [imgValue];
  }
  return [];
}

function toImageDataUrl(value) {
  return value.startsWith('data:image/') ? value : `data:image/png;base64,${value}`;
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