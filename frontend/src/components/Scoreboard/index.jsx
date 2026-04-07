import { useEffect } from 'react';
import { getLeaderboard } from '../../api/client';
import useGameStore from '../../store/gameSlice';
import styles from './Scoreboard.module.css';

export default function Scoreboard() {
  const { leaderboard, setLeaderboard } = useGameStore((s) => ({
    leaderboard: s.leaderboard,
    setLeaderboard: s.setLeaderboard,
  }));

  useEffect(() => {
    getLeaderboard()
      .then((res) => {
        if (typeof setLeaderboard === 'function') {
          setLeaderboard(res.data.results ?? res.data);
        }
      })
      .catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!leaderboard?.length) return null;

  return (
    <div className={styles.board}>
      <h3 className={styles.title}>🏅 Leaderboard</h3>
      <ol className={styles.list}>
        {leaderboard.slice(0, 10).map((entry) => (
          <li key={entry.id} className={styles.entry}>
            <span className={styles.player}>{entry.player_name}</span>
            <span className={styles.level}>{entry.level_title}</span>
            <span className={styles.points}>{entry.points} pts</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
