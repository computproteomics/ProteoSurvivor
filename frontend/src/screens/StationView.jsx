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

  const isSamplePrep = stationId === 'sample_prep';
  const [phase, setPhase] = useState(isSamplePrep ? 'welcome' : 'default');

  const content = {
    title: getStationTitle(stationId),
    description: getStationDescription(stationId),
    objective: 'Configure and run this station before returning to the map.',
  };

  useEffect(() => {
    if (!stationId) return;

    setPhase(stationId === 'sample_prep' ? 'welcome' : 'default');
    setLoading(true);

    enterStation(stationId, sessionId)
      .then((res) => setStationData(res.data))
      .catch(() => {
        setStationData({
          message: "Entered station '" + stationId + "' successfully.",
          station_id: stationId,
        });
      })
      .finally(() => setLoading(false));
  }, [stationId, sessionId]);

  function goToParams() {
    navigate('/station/' + stationId + '/params');
  }

  function renderSamplePrepFlow() {
    if (phase === 'welcome') {
      return (
        <>
          <h1 className={styles.title}>Welcome to Sample Preparation</h1>
          <p className={styles.text}>
            In this station you will learn how to prep your sample for LC/MS.
          </p>

          <div className={styles.buttonRow}>
            <button className={styles.secondaryButton} onClick={() => navigate('/world')}>
              Back to map
            </button>
            <button
              className={styles.primaryButton}
              onClick={() => setPhase('video')}
              disabled={loading}
            >
              Continue
            </button>
          </div>
        </>
      );
    }

    if (phase === 'video') {
      return (
        <>
          <h1 className={styles.title}>Sample Prep Walkthrough</h1>
          <div className={styles.mediaWrap}>
            <video
              className={styles.video}
              src="/media/sample_prep_vid.mp4"
              controls
              autoPlay
              playsInline
            />
          </div>
          <p className={styles.info}>Watch the videos above or skip to the next steps ahead.</p>

          <div className={styles.buttonRow}>
            <button className={styles.secondaryButton} onClick={() => setPhase('welcome')}>
              Back
            </button>
            <button className={styles.primaryButton} onClick={() => setPhase('done')}>
              Skip video
            </button>
          </div>
        </>
      );
    }

    return (
      <>
        <h1 className={styles.title}>Sample Preparation Completed</h1>
        <p className={styles.text}>
          Great work. The station intro is complete and your sample prep is marked successful.
        </p>

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
          <button className={styles.primaryButton} onClick={goToParams}>
            Configure and Run
          </button>
        </div>
      </>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        {loading && <p className={styles.info}>Loading station…</p>}

        {isSamplePrep ? (
          renderSamplePrepFlow()
        ) : (
          <>
            <h1 className={styles.title}>{content.title}</h1>
            <p className={styles.text}>{content.description}</p>

            <div className={styles.box}>
              <strong>Objective:</strong>
              <p className={styles.boxText}>{content.objective}</p>
            </div>

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
                onClick={goToParams}
                disabled={loading}
              >
                Configure and Run →
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}