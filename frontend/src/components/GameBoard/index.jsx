import { useState } from 'react';
import useGameStore from '../../store/gameSlice';
import DataTable from '../DataTable';
import ChartViewer from '../ChartViewer';
import styles from './GameBoard.module.css';
export default function GameBoard({ onSubmit }) {
  const { dataset, currentLevel } = useGameStore();
  const [activeTab, setActiveTab] = useState('table');

  if (!dataset) return null;

  const { rows, columns, metadata } = dataset;

  return (
    <div className={styles.board}>
      <div className={styles.header}>
        <h2>{currentLevel?.title ?? 'Challenge'}</h2>
        <p className={styles.task}>{metadata?.task}</p>
      </div>

      <div className={styles.tabs}>
        <button
          className={activeTab === 'table' ? styles.active : ''}
          onClick={() => setActiveTab('table')}
        >
          Table
        </button>
        <button
          className={activeTab === 'chart' ? styles.active : ''}
          onClick={() => setActiveTab('chart')}
        >
          Chart
        </button>
      </div>

      <div className={styles.content}>
        {activeTab === 'table' ? (
          <DataTable columns={columns} rows={rows} metadata={metadata} onSubmit={onSubmit} />
        ) : (
          <ChartViewer columns={columns} rows={rows} metadata={metadata} onSubmit={onSubmit} />
        )}
      </div>
    </div>
  );
}
