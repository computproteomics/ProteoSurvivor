import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { enterStation, runStation } from '../api/client';
import useGameStore from '../store/gameSlice';
import {
  getStationBackgroundImage,
  getStationDescription,
  getStationExpectations,
  getStationObjective,
  getStationStatusMessages,
  getStationTitle,
} from '../assets/stationConfig';
import styles from './StationView.module.css';

const INTRO_VIDEO_STATIONS = {
  sample_prep: {
    welcomeTitle: 'Welcome to Sample Preparation',
    welcomeText: 'In this station you will learn how to prep your sample for LC/MS.',
    videoTitle: 'Sample Prep Walkthrough',
    videoSrc: '/media/sample_prep_vid.mp4',
    doneTitle: 'Sample Preparation Completed',
    doneText: 'Finalizing sample prep with backend validation.',
  },
  mass_spec: {
    welcomeTitle: 'Welcome to Mass Spectrometry',
    welcomeText: 'In this station you will learn the core MS acquisition workflow.',
    videoTitle: 'Mass Spectrometry Walkthrough',
    videoSrc: '/media/ms_run.mp4',
    doneTitle: 'Mass Spectrometry Completed',
    doneText: 'Finalizing mass spectrometry with backend validation.',
  },
};

export default function StationView() {
  const { stationId } = useParams();
  const navigate = useNavigate();
  const { sessionId, markStationComplete } = useGameStore();

  const [stationData, setStationData] = useState(null);
  const [loading, setLoading] = useState(false);

  const introConfig = stationId ? INTRO_VIDEO_STATIONS[stationId] : null;
  const hasIntroVideoFlow = Boolean(introConfig);

  const [phase, setPhase] = useState(hasIntroVideoFlow ? 'welcome' : 'default');
  const [stationResult, setStationResult] = useState(null);
  const [submittingStationResult, setSubmittingStationResult] = useState(false);
  const [videoEnded, setVideoEnded] = useState(false);
  const statusMessages = getStationStatusMessages(stationId);

  const content = {
    title: getStationTitle(stationId),
    description: getStationDescription(stationId),
    objective: getStationObjective(stationId),
    expectations: getStationExpectations(stationId),
  };

  function renderObjectiveAndExpectations() {
    return (
      <>
        <div className={styles.box}>
          <strong>Objective:</strong>
          <p className={styles.boxText}>{content.objective}</p>
        </div>

        {content.expectations && (
          <div className={styles.box}>
            <strong>Expectations:</strong>
            <p className={styles.boxText}>{content.expectations}</p>
          </div>
        )}
      </>
    );
  }

  const stationBackground = getStationBackgroundImage(stationId);
  const pageStyle = stationBackground
    ? {
      backgroundImage: `linear-gradient(rgba(15, 23, 42, 0.5), rgba(15, 23, 42, 0.5)), url(${stationBackground})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
    }
    : undefined;

  useEffect(() => {
    if (!stationId) return;

    setPhase(INTRO_VIDEO_STATIONS[stationId] ? 'welcome' : 'default');
    setStationResult(null);
    setVideoEnded(false);

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

  useEffect(() => {
    if (!hasIntroVideoFlow || !stationId) return;
    if (phase !== 'done' || stationResult || submittingStationResult) return;

    setSubmittingStationResult(true);
    runStation(stationId, {})
      .then((res) => {
        setStationResult({
          success: Boolean(res.data?.success),
          feedback: res.data?.feedback || 'Station completed.',
        });
      })
      .catch(() => {
        setStationResult({
          success: false,
          feedback: 'Could not validate station completion with backend.',
        });
      })
      .finally(() => setSubmittingStationResult(false));
  }, [hasIntroVideoFlow, phase, stationResult, submittingStationResult, stationId]);

  function goToParams() {
    navigate('/station/' + stationId + '/params');
  }

  function finishIntroStation() {
    if (stationResult?.success === true) {
      markStationComplete(stationId);
    }
    navigate('/world');
  }

  function startVideoPhase() {
    setVideoEnded(false);
    setPhase('video');
  }

  function renderIntroVideoStationFlow() {
    if (!introConfig) return null;

    if (phase === 'welcome') {
      return (
        <>
          <h1 className={styles.title}>{introConfig.welcomeTitle}</h1>
          <p className={styles.text}>{introConfig.welcomeText}</p>
          {renderObjectiveAndExpectations()}

          <div className={styles.buttonRow}>
            <button className={styles.secondaryButton} onClick={() => navigate('/world')}>
              Back to map
            </button>
            <button
              className={styles.primaryButton}
              onClick={startVideoPhase}
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
          <h1 className={styles.title}>{introConfig.videoTitle}</h1>
          <div className={styles.mediaWrap}>
            <video
              className={styles.video}
              src={introConfig.videoSrc}
              controls
              autoPlay
              playsInline
              onEnded={() => setVideoEnded(true)}
            />
          </div>
          <p className={styles.info}>Watch the video above or skip to the next steps ahead.</p>
          {renderObjectiveAndExpectations()}

          <div className={styles.buttonRow}>
            <button className={styles.secondaryButton} onClick={() => setPhase('welcome')}>
              Back
            </button>
            <button className={styles.secondaryButton} onClick={() => setPhase('done')}>
              Skip video
            </button>
            {videoEnded && (
              <button className={styles.primaryButton} onClick={() => setPhase('done')}>
                Continue
              </button>
            )}
          </div>
        </>
      );
    }

    return (
      <>
        <h1 className={styles.title}>{introConfig.doneTitle}</h1>
        <p className={styles.text}>{introConfig.doneText}</p>
        {renderObjectiveAndExpectations()}

        {submittingStationResult && <p className={styles.info}>{statusMessages.submitting}</p>}

        {stationResult && (
          <div className={styles.box}>
            <strong>Status:</strong>
            <p className={styles.boxText}>
              {stationResult.success ? statusMessages.success : statusMessages.failed}
            </p>
            <p className={styles.boxText}>{stationResult.feedback}</p>
          </div>
        )}

        <div className={styles.buttonRow}>
          <button className={styles.secondaryButton} onClick={startVideoPhase}>
            Back to video
          </button>
          <button
            className={styles.primaryButton}
            onClick={finishIntroStation}
            disabled={submittingStationResult || !stationResult}
          >
            Back to map
          </button>
        </div>
      </>
    );
  }

  return (
    <div className={styles.page} style={pageStyle}>
      <div className={styles.card}>
        {loading && <p className={styles.info}>Loading station...</p>}

        {hasIntroVideoFlow ? (
          renderIntroVideoStationFlow()
        ) : (
          <>
            <h1 className={styles.title}>{content.title}</h1>
            <p className={styles.text}>{content.description}</p>
            {renderObjectiveAndExpectations()}

            {stationData && !loading && (
              <div className={styles.box}>
                <strong>Status:</strong>
                <p className={styles.boxText}>{statusMessages.entered}</p>
                {stationData.message && stationData.message !== statusMessages.entered && (
                  <p className={styles.boxText}>{stationData.message}</p>
                )}
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