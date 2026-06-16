import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { startGame } from '../api/client';
import useGameStore from '../store/gameSlice';
import introBackground from '../assets/backgrounds/Introduction.webp';
import styles from './Intro.module.css';

export default function Intro() {
  const navigate = useNavigate();
  const userName = useGameStore((s) => s.userName);
  const userId = useGameStore((s) => s.userId);
  const setPlayerProfile = useGameStore((s) => s.setPlayerProfile);
  const startLabSession = useGameStore((s) => s.startLabSession);

  const [nameInput, setNameInput] = useState(userName ?? '');
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState('');

  async function handleStart() {
    const cleanName = nameInput.trim();
    if (!cleanName) return;

    setStartError('');
    setIsStarting(true);

    try {
      const { data } = await startGame({ userName: cleanName });
      const stableUserId = data.user_id;
      const nextSessionId = data.session_id || `${stableUserId}_${Date.now()}`;

      setPlayerProfile({ userId: stableUserId, userName: data.user_name || cleanName });
      startLabSession(nextSessionId);
      navigate('/news');
    } catch {
      setStartError('Could not start the game right now. Please try again.');
    } finally {
      setIsStarting(false);
    }
  }

  const pageStyle = {
    backgroundImage: `linear-gradient(rgba(15, 23, 42, 0.5), rgba(15, 23, 42, 0.5)), url(${introBackground})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat',
  };

  return (
    <div className={styles.page} style={pageStyle}>
      <div className={styles.card}>
        <h1 className={styles.title}>🔬 Welcome to the Proteomics Game</h1>
        <p className={styles.description}>
          Step into the role of a computational proteomics researcher. Guide samples from
          preparation through mass spectrometry, database search, and data analysis — then
          report your findings.
        </p>

        <div className={styles.formRow}>
          <label className={styles.label} htmlFor="playerName">
            Your name
          </label>
          <input
            id="playerName"
            className={styles.input}
            type="text"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            placeholder="Enter your name"
            maxLength={64}
          />
          {userId && <p className={styles.userId}>User ID: {userId}</p>}
          {startError && <p className={styles.errorText}>{startError}</p>}
        </div>

        <button
          className={styles.startButton}
          onClick={handleStart}
          disabled={!nameInput.trim() || isStarting}
        >
          {isStarting ? 'Starting...' : 'Start'}
        </button>
      </div>
    </div>
  );
}
