import { useNavigate } from 'react-router-dom';
import useGameStore from '../store/gameSlice';
import styles from './AssignmentIntro.module.css';

export default function AssignmentIntro() {
  const navigate = useNavigate();
  const userName = useGameStore((s) => s.userName);
  const playerName = userName || 'Researcher';

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>🧭 Mission Briefing</h1>
        <p className={styles.lead}>
          Welcome, Dr. {playerName}. Your assignment is to investigate the outbreak dataset
          and submit a strong final report based on your proteomics workflow decisions.
        </p>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Your task</h2>
          <ul className={styles.list}>
            <li>Visit lab stations on the map and complete each part of the workflow.</li>
            <li>Choose station parameters carefully and evaluate the resulting data quality.</li>
            <li>Reach the final report station and hand in your interpretation.</li>
          </ul>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Tips for the map and lab</h2>
          <ul className={styles.list}>
            <li>Move with arrow keys/WASD or click stations directly on the map.</li>
            <li>Stations can be completed in any order, but every choice affects later results.</li>
            <li>Use each station objective to guide what “good” output should look like.</li>
          </ul>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Learning goals</h2>
          <ul className={styles.list}>
            <li>Understand key steps in a computational proteomics workflow.</li>
            <li>Practice how preprocessing and statistical choices shape conclusions.</li>
            <li>Learn to justify a biological interpretation from quantitative results.</li>
          </ul>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Links to further educational material</h2>
          <ul className={styles.list}>
            <li>
              <a
               href="https://training.bmb.sdu.dk/courses/course-v1:University_of_Southern_Denmark+SDU_BMB_COMPPROT+2022_KI/about"
               target="_blank"
               rel="noopener noreferrer"
              >
                Online course: Computational Proteomics
              </a>
              <span> — University of Southern Denmark, sign up for free</span>
            </li>

            <li>
              <a
                href="https://tess.elixir-europe.org/search?q=proteomics#materials"
                target="_blank"
                rel="noopener noreferrer"
              >
                Proteomics training materials
              </a>
              <span> — ELIXIR Training eSupport System</span>
            </li>
          </ul>
        </section>

        <button type="button" className={styles.startButton} onClick={() => navigate('/world')}>
          Enter the lab
        </button>
      </div>
    </div>
  );
}
