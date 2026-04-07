import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getLevelDataset, createSession, submitAnswer } from '../api/client';
import useGameStore from '../store/gameSlice';
import GameBoard from '../components/GameBoard';
import styles from './Game.module.css';

export default function Game() {
  const { levelId } = useParams();
  const navigate = useNavigate();
  const {
    levels,
    setCurrentLevel,
    setCurrentSession,
    setDataset,
    setLoading,
    setError,
    startTimer,
    getElapsedSeconds,
    isLoading,
    error,
  } = useGameStore();

  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    const level = levels.find((l) => String(l.id) === levelId);
    if (level) setCurrentLevel(level);

    setLoading(true);
    Promise.all([
      getLevelDataset(levelId),
      createSession(Number(levelId)),
    ])
      .then(([datasetRes, sessionRes]) => {
        setDataset(datasetRes.data);
        setCurrentSession(sessionRes.data);
        setSessionId(sessionRes.data.id);
        startTimer();
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [levelId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = async (answer) => {
    const elapsed = getElapsedSeconds();
    try {
      await submitAnswer(sessionId, answer, elapsed);
      navigate(`/results/${sessionId}`);
    } catch (err) {
      setError(err.message);
    }
  };

  if (isLoading) return <p className={styles.status}>Loading challenge…</p>;
  if (error) return <p className={styles.error}>Error: {error}</p>;

  return (
    <div className={styles.page}>
      <GameBoard onSubmit={handleSubmit} />
    </div>
  );
}
