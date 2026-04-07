import useGameStore from '../../store/gameSlice';
import styles from './LevelSelector.module.css';

export default function LevelSelector({ onSelect }) {
  const { levels, isLoading } = useGameStore();

  const difficultyLabel = (d) => '⭐'.repeat(d);

  if (isLoading) return <p>Loading levels…</p>;
  if (!levels.length) return <p>No levels available.</p>;

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Choose a Level</h3>
      <ul className={styles.list}>
        {levels.map((level) => (
          <li key={level.id} className={styles.card} onClick={() => onSelect(level)}>
            <div className={styles.top}>
              <span className={styles.levelTitle}>{level.title}</span>
              <span className={styles.difficulty}>{difficultyLabel(level.difficulty)}</span>
            </div>
            <p className={styles.desc}>{level.description}</p>
            <span className={styles.type}>{level.challenge_type}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
