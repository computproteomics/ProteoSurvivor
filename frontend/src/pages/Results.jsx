import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import useGameStore from '../store/gameSlice';
import styles from './Results.module.css';

export default function Results() {
  const { sessionId } = useParams();
  const { score, currentLevel, reset } = useGameStore();

  useEffect(() => {
    return () => {
      reset();
    };
  }, [reset]);

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>🏆 Results</h1>
      {score ? (
        <div className={styles.card}>
          <p className={styles.points}>{score.points} pts</p>
          <p className={styles.time}>Time: {score.time_taken_seconds}s</p>
          <p className={styles.feedback}>{score.feedback}</p>
        </div>
      ) : (
        <p>No score data available for session {sessionId}.</p>
      )}
      <div className={styles.actions}>
        <Link to="/" className={styles.btn}>
          ← Back to levels
        </Link>
      </div>
    </div>
  );
}
