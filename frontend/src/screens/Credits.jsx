import { useNavigate } from 'react-router-dom';
import { version } from '../../package.json';
import styles from './Credits.module.css';

const RESEARCH_GROUPS = [
  {
    name: 'Computational Proteomics Group',
    url: 'https://computproteomics.bmb.sdu.dk',
    description: 'Methods and software for large-scale analysis of proteomics data.',
 },
  {
    name: 'Protein Research Group',
    url: 'https://www.sdu.dk/en/forskning/protein',
    description: 'Structural and functional characterisation of proteins at SDU.',
  },
  {
    name: 'University of Southern Denmark',
    url: 'https://sdu.dk',
    description: 'SDU — host institution and academic home of this project.',
  },
];

const CONTRIBUTORS = [
  { name: 'Christine Lærke Jensen',    github: 'chje118' },
  { name: 'Edgar Luis Lämmerhirt',    github: 'zahnpasta-aus-der-tube' },    
  { name: 'Jakob Gad Spoorendonk',     github: 'Trenchcoat-capybara' },
  { name: 'Lev Levitsky',              github: 'levitsky' },
  { name: 'Magnus Mørkeberg',          github: 'Mmoerkeberg' },
  { name: 'Maja Lindskow Jessen',      github: 'MajaLindskov' },
  { name: 'Malthe Letting',            github: 'M-Letting' },
  { name: 'Veit Schwämmle',            github: 'veitveit' },
];

const TECH_STACK = [
  { label: 'Frontend', value: 'React 18, Vite, React Router, Zustand, Recharts' },
  { label: 'Backend', value: 'Django 4.2, Django REST Framework, pandas, numpy' },
  { label: 'Database', value: 'SQLite (dev) / PostgreSQL (prod)' },
  { label: 'Deployment', value: 'Docker, nginx, supervisord' },
];

export default function Credits() {
  const navigate = useNavigate();

  return (
    <div className={styles.page}>
      <div className={styles.shell}>

        <div className={styles.hero}>
          <div>
            <p className={styles.kicker}>About this project</p>
            <h1 className={styles.title}>Credits</h1>
            <p className={styles.subtitle}>
              ProteoSurviver is an open-source browser game for learning computational
              proteomics — built by researchers and students at the University of Southern Denmark.
            </p>
            <p className={styles.versionBadge}>v{version}</p>
          </div>
          <button className={styles.backButton} onClick={() => navigate('/world')}>
            Back to map
          </button>
        </div>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Research Groups</h2>
          <div className={styles.groupGrid}>
            {RESEARCH_GROUPS.map((group) => (
              <a
                key={group.url}
                href={group.url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.groupCard}
              >
                <span className={styles.groupName}>{group.name}</span>
                <span className={styles.groupDesc}>{group.description}</span>
                <span className={styles.groupLink}>{group.url}</span>
              </a>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Contributors</h2>
          <div className={styles.contributorGrid}>
            {CONTRIBUTORS.map((person) => (
              <a
                key={person.github}
                href={`https://github.com/${person.github}`}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.contributorCard}
              >
                <img
                  className={styles.avatar}
                  src={`https://github.com/${person.github}.png?size=80`}
                  alt={person.name}
                  width={40}
                  height={40}
                />
                <span className={styles.contributorName}>{person.name}</span>
              </a>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Technology</h2>
          <dl className={styles.techList}>
            {TECH_STACK.map((item) => (
              <div key={item.label} className={styles.techRow}>
                <dt className={styles.techLabel}>{item.label}</dt>
                <dd className={styles.techValue}>{item.value}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Source Code &amp; License</h2>
          <p className={styles.licenseText}>
            ProteoSurviver is open source.{' '}
            <a
              href="https://github.com/computproteomics/ProteoSurviver"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.inlineLink}
            >
              View the repository on GitHub
            </a>
            {' '}to contribute or inspect the simulation code. Found a bug?{' '}
            <a
              href="https://github.com/computproteomics/ProteoSurviver/issues"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.inlineLink}
            >
              Open an issue
            </a>
            .
          </p>
        </section>

      </div>
    </div>
  );
}

