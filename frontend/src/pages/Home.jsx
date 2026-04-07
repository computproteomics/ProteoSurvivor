import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getLevels } from '../api/client';
import useGameStore from '../store/gameSlice';
import LevelSelector from '../components/LevelSelector';
import Scoreboard from '../components/Scoreboard';
import styles from './Home.module.css';

export default function Home() {
  const { setLevels, setLoading, setError } = useGameStore();
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    getLevels()
      .then((res) => setLevels(res.data.results ?? res.data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [setLevels, setLoading, setError]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>🔬 Data Analysis Game</h1>
        <p>Sharpen your data skills — one challenge at a time.</p>
      </header>
      <main className={styles.main}>
        <LevelSelector onSelect={(level) => navigate(`/game/${level.id}`)} />
        <Scoreboard />
      </main>
    </div>
  );
}
