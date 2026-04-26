import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import useGameStore from '../store/gameSlice';
import { getStationBackgroundImage, getStationTitle } from '../assets/stationConfig';
import { getStationResultsRenderer } from './resultRenderer';
import styles from './StationResults.module.css';

export default function StationResults() {
  // Read the current station from the route.
  const { stationId } = useParams();
  const navigate = useNavigate();
  // Pull the latest station output and completion action from shared state.
  const { stationResults, markStationComplete } = useGameStore();
  const [zoomedImageIndex, setZoomedImageIndex] = useState(null);

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
  const didRunSucceed = stationResults?.success === true;

  function handleBackToMap() {
    // Only successful runs should count as completed stations.
    if (didRunSucceed) {
      markStationComplete(stationId);
    }
    navigate('/world');
  }

  function handleRetry() {
    // Let the user adjust the same station parameters again.
    navigate(`/station/${stationId}/params`);
  }

  if (!stationResults) {
    return (
      <div className={styles.page} style={pageStyle}>
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

  const StationResultContent = getStationResultsRenderer(stationId, { onImageClick: setZoomedImageIndex });

  return (
    <div className={styles.page} style={pageStyle}>
      <div className={styles.card}>
        <div className={styles.headerRow}>
          <span className={styles.stationBadge}>{title}</span>
          <span className={styles.completeBadge}>
            {didRunSucceed ? '✅ Run complete' : '⚠️ Run failed'}
          </span>
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

      {zoomedImageIndex !== null && stationResults?.img && (
        <ImageZoomModal
          imageIndex={zoomedImageIndex}
          images={normalizeImageList(stationResults.img)}
          onClose={() => setZoomedImageIndex(null)}
          onNavigate={(index) => setZoomedImageIndex(index)}
        />
      )}
    </div>
  );
}

function normalizeImageList(imgValue) {
  if (Array.isArray(imgValue)) {
    return imgValue.filter((value) => typeof value === 'string' && value.trim().length > 0);
  }
  if (typeof imgValue === 'object' && imgValue !== null) {
    return Object.values(imgValue).filter(
      (value) => typeof value === 'string' && value.trim().length > 0
    );
  }
  if (typeof imgValue === 'string' && imgValue.trim().length > 0) {
    return [imgValue];
  }
  return [];
}

function toImageDataUrl(value) {
  return value.startsWith('data:image/') ? value : `data:image/png;base64,${value}`;
}

function ImageZoomModal({ imageIndex, images, onClose, onNavigate }) {
  const currentImage = images[imageIndex];
  const totalImages = images.length;

  function handlePrevious() {
    onNavigate((imageIndex - 1 + totalImages) % totalImages);
  }

  function handleNext() {
    onNavigate((imageIndex + 1) % totalImages);
  }

  return (
    <div className={styles.modalOverlay} role="presentation" onClick={onClose}>
      <div
        className={styles.modalWindow}
        role="dialog"
        aria-modal="true"
        aria-label="Result plot zoom"
        onClick={(event) => event.stopPropagation()}
      >
        <div className={styles.modalHeader}>
          <h2 className={styles.modalTitle}>
            Result Plot {imageIndex + 1} of {totalImages}
          </h2>
          <button className={styles.modalCloseButton} onClick={onClose}>
            Close
          </button>
        </div>

        <div className={styles.modalImageWrap}>
          <img
            src={toImageDataUrl(currentImage)}
            alt={`Result plot ${imageIndex + 1}`}
            className={styles.modalImage}
          />
        </div>

        {totalImages > 1 && (
          <div className={styles.modalNavigation}>
            <button className={styles.modalNavButton} onClick={handlePrevious}>
              ← Previous
            </button>
            <span className={styles.modalNavInfo}>
              {imageIndex + 1} / {totalImages}
            </span>
            <button className={styles.modalNavButton} onClick={handleNext}>
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
