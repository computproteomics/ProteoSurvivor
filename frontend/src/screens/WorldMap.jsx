import { useNavigate } from 'react-router-dom';
import useGameStore from '../store/gameSlice';
import styles from './WorldMap.module.css';

const STATIONS = [
  { id: 'sample_prep', label: 'Sample Preparation' },
  { id: 'mass_spec', label: 'Mass Spectrometer' },
  { id: 'search_setup', label: 'Search Engine Setup' },
  { id: 'data_analysis', label: 'Data Analysis' },
  { id: 'veit', label: 'Veit' },
];

export default function WorldMap() {
  const navigate = useNavigate();
  const completedStations = useGameStore((s) => s.completedStations);

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>World Map</h1>
      <ul className={styles.stationList}>
        {STATIONS.map((station) => {
          const done = completedStations.includes(station.id);
          return (
            <li key={station.id}>
              <button
                className={`${styles.stationButton} ${done ? styles.done : ''}`}
                onClick={() => navigate(`/station/${station.id}`)}
              >
                {done ? '✅ ' : ''}{station.label}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
