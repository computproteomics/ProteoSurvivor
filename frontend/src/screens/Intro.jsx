import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useGameStore from '../store/gameSlice';
import styles from './Intro.module.css';

export default function Intro() {
  const navigate = useNavigate();
  const userName = useGameStore((s) => s.userName);
  const userId = useGameStore((s) => s.userId);
  const setPlayerProfile = useGameStore((s) => s.setPlayerProfile);
  const startLabSession = useGameStore((s) => s.startLabSession);

  const [nameInput, setNameInput] = useState(userName ?? '');

  function handleStart() {
    const cleanName = nameInput.trim();
    if (!cleanName) return;

    const stableUserId = userId || `user_${Date.now()}`;
    const nextSessionId = `${stableUserId}_${Date.now()}`;

    setPlayerProfile({ userId: stableUserId, userName: cleanName });
    startLabSession(nextSessionId);
    navigate('/world');
  }

  return (
    <div className={styles.page}>
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
        </div>

        <button className={styles.startButton} onClick={handleStart} disabled={!nameInput.trim()}>
          Start
        </button>
      </div>
    </div>
  );
}
