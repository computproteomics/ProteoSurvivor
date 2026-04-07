import { useState } from 'react';
import {
  ScatterChart,
  Scatter,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import styles from './ChartViewer.module.css';

export default function ChartViewer({ columns, rows, metadata, onSubmit }) {
  const [chosen, setChosen] = useState('');

  const isScatter = columns.includes('x') && columns.includes('y');
  const isTimeSeries = columns.includes('time') && columns.includes('value');
  const options = metadata?.options ?? [];

  const handleSubmit = () => {
    const payload = isScatter
      ? { correlation_type: chosen, correct_correlation_type: metadata?.correct_correlation_type }
      : { trend: chosen, correct_trend: metadata?.correct_trend };
    onSubmit(payload);
  };

  return (
    <div className={styles.viewer}>
      <div className={styles.chart}>
        <ResponsiveContainer width="100%" height={320}>
          {isScatter ? (
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="x" name="X" />
              <YAxis dataKey="y" name="Y" />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Scatter data={rows} fill="#3182ce" />
            </ScatterChart>
          ) : isTimeSeries ? (
            <LineChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#38a169" dot={false} />
            </LineChart>
          ) : (
            <p>No chart available for this challenge type.</p>
          )}
        </ResponsiveContainer>
      </div>

      {options.length > 0 && (
        <div className={styles.options}>
          <p className={styles.prompt}>{metadata?.task}</p>
          <div className={styles.btnGroup}>
            {options.map((opt) => (
              <button
                key={opt}
                className={`${styles.optBtn} ${chosen === opt ? styles.active : ''}`}
                onClick={() => setChosen(opt)}
              >
                {opt}
              </button>
            ))}
          </div>
          <button className={styles.submitBtn} disabled={!chosen} onClick={handleSubmit}>
            Submit Answer
          </button>
        </div>
      )}
    </div>
  );
}
