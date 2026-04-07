import { useNavigate } from 'react-router-dom';
import styles from './Intro.module.css';

export default function Intro() {
  const navigate = useNavigate();

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>🔬 Welcome to the Proteomics Game</h1>
        <p className={styles.description}>
          Step into the role of a computational proteomics researcher. Guide samples from
          preparation through mass spectrometry, database search, and data analysis — then
          report your findings.
        </p>
        <button className={styles.startButton} onClick={() => navigate('/world')}>
          Start
        </button>
      </div>
    </div>
  );
}
