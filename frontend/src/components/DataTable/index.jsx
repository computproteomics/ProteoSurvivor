import { useState } from 'react';
import styles from './DataTable.module.css';

export default function DataTable({ columns, rows, metadata, onSubmit }) {
  const [selectedIndices, setSelectedIndices] = useState([]);

  const toggle = (rowId) => {
    setSelectedIndices((prev) =>
      prev.includes(rowId) ? prev.filter((i) => i !== rowId) : [...prev, rowId]
    );
  };

  const handleSubmit = () => {
    onSubmit({
      selected_indices: selectedIndices,
      correct_indices: metadata?.outlier_indices ?? metadata?.dirty_indices ?? [],
    });
  };

  return (
    <div>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Select</th>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row.id ?? i}
              className={selectedIndices.includes(i) ? styles.selected : ''}
              onClick={() => toggle(i)}
            >
              <td>
                <input
                  type="checkbox"
                  checked={selectedIndices.includes(i)}
                  onChange={() => toggle(i)}
                  onClick={(e) => e.stopPropagation()}
                />
              </td>
              {columns.map((col) => (
                <td key={col}>{row[col] ?? <em className={styles.null}>null</em>}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <button className={styles.submitBtn} onClick={handleSubmit}>
        Submit Answer
      </button>
    </div>
  );
}
