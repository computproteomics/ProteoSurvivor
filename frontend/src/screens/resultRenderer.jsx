import { useEffect, useMemo, useState } from 'react';
import styles from './StationResults.module.css';

const TABLE_ROW_KEY_COLUMNS = ['Protein ID', 'Protein', 'Gene'];

export function getStationResultsRenderer(stationId, handlers = {}) {
  const { onImageClick } = handlers;

  if (stationId === 'data_review') {
    return (props) => <DataReviewResultsContent {...props} onImageClick={onImageClick} />;
  }

  return (props) => <GenericStationResultsContent {...props} onImageClick={onImageClick} />;
}

function GenericStationResultsContent({ stationResults, onImageClick }) {
  const { summary, recommendation, feedback, img, ...detailFields } = stationResults;
  const resultImages = normalizeImageList(img);

  return (
    <>
      {summary && (
        <div className={styles.summaryBox}>
          {/* Short summary shown above the raw result fields. */}
          <p className={styles.summaryText}>{summary}</p>
        </div>
      )}

      {Object.keys(detailFields).length > 0 && (
        <table className={styles.table}>
          <tbody>
            {/* Render every remaining field as a simple key/value row. */}
            {Object.entries(detailFields).map(([key, value]) => (
              <tr key={key} className={styles.row}>
                <td className={styles.key}>{formatKey(key)}</td>
                <td className={styles.value}>{formatValue(value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {typeof feedback === 'string' && feedback.trim().length > 0 && (
        <div className={styles.recommendationBox}>
          <strong>Feedback</strong>
          {renderTextOrHtml(feedback, styles.recommendationText)}
        </div>
      )}

      {resultImages.length > 0 && (
        <div className={styles.imageSection}>
          <h2 className={styles.imageTitle}>Result Plots</h2>
          <div className={styles.imageGrid}>
            {resultImages.map((imageSrc, index) => (
              <figure
                key={index}
                className={styles.imageCard}
                onClick={() => onImageClick && onImageClick(index)}
                role={onImageClick ? 'button' : undefined}
                tabIndex={onImageClick ? 0 : undefined}
                onKeyDown={(e) => {
                  if (onImageClick && (e.key === 'Enter' || e.key === ' ')) {
                    e.preventDefault();
                    onImageClick(index);
                  }
                }}
              >
                <img
                  src={toImageDataUrl(imageSrc)}
                  alt={`Result plot ${index + 1}`}
                  className={styles.resultImage}
                />
                {onImageClick && <div className={styles.imageHint}>Click to enlarge</div>}
              </figure>
            ))}
          </div>
        </div>
      )}

      {recommendation && (
        <div className={styles.recommendationBox}>
          <strong>💡 Recommendation:</strong>
          <p className={styles.recommendationText}>{recommendation}</p>
        </div>
      )}
    </>
  );
}

function DataReviewResultsContent({ stationResults, onImageClick }) {
  const {
    summary,
    feedback,
    recommendation,
    img,
    metric_cards: metricCards = [],
    sample_metrics: sampleMetrics = [],
    organism_breakdown: organismBreakdown = [],
    column_explanations: columnExplanations = [],
    table_preview: tablePreview,
  } = stationResults;
  const resultImages = normalizeImageList(img);
  const tableColumns = useMemo(() => tablePreview?.columns ?? [], [tablePreview]);
  const tableRows = useMemo(() => tablePreview?.rows ?? [], [tablePreview]);
  const [columnFilters, setColumnFilters] = useState({});
  const [sortColumn, setSortColumn] = useState('');
  const [sortDirection, setSortDirection] = useState('asc');

  useEffect(() => {
    if (tableColumns.length === 0) {
      setSortColumn('');
      return;
    }
    if (!tableColumns.includes(sortColumn)) {
      setSortColumn(tableColumns[0]);
    }
  }, [sortColumn, tableColumns]);

  useEffect(() => {
    setColumnFilters((currentFilters) =>
      Object.fromEntries(
        Object.entries(currentFilters).filter(([column]) => tableColumns.includes(column))
      )
    );
  }, [tableColumns]);

  const activeColumnFilters = useMemo(
    () =>
      Object.fromEntries(
        tableColumns
          .map((column) => [column, (columnFilters[column] ?? '').trim().toLowerCase()])
          .filter(([, filterValue]) => filterValue.length > 0)
      ),
    [columnFilters, tableColumns]
  );

  const filteredAndSortedRows = useMemo(() => {
    const filteredRows =
      Object.keys(activeColumnFilters).length === 0
        ? tableRows
        : tableRows.filter((row) =>
            Object.entries(activeColumnFilters).every(([column, filterValue]) =>
              getTableCellSearchText(row[column]).includes(filterValue)
            )
          );

    if (!sortColumn) {
      return filteredRows;
    }

    return [...filteredRows].sort((leftRow, rightRow) => {
      const comparison = compareTableValues(leftRow[sortColumn], rightRow[sortColumn]);
      return sortDirection === 'desc' ? comparison * -1 : comparison;
    });
  }, [activeColumnFilters, sortColumn, sortDirection, tableRows]);

  const totalFilteredRows = filteredAndSortedRows.length;
  const hasActiveFilter = Object.keys(activeColumnFilters).length > 0;
  const rangeLabel =
    totalFilteredRows === 0
      ? 'Showing 0 rows'
      : hasActiveFilter
        ? `Showing ${totalFilteredRows} filtered rows`
        : `Showing all ${totalFilteredRows} rows`;

  return (
    <>
      {summary && (
        <div className={styles.summaryBox}>
          <p className={styles.summaryText}>{summary}</p>
        </div>
      )}

      {metricCards.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Quick metrics</h2>
          <div className={styles.metricGrid}>
            {metricCards.map((metric) => (
              <article key={metric.label} className={styles.metricCard}>
                <p className={styles.metricLabel}>{metric.label}</p>
                <p className={styles.metricValue}>{metric.value}</p>
                <p className={styles.metricDescription}>{metric.description}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      {sampleMetrics.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Per-sample intensity summary</h2>
          <div className={styles.dataTableWrap}>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>Sample</th>
                  <th>Median</th>
                  <th>Min</th>
                  <th>Max</th>
                  <th>Missing</th>
                </tr>
              </thead>
              <tbody>
                {sampleMetrics.map((sample) => (
                  <tr key={sample.sample}>
                    <td>{sample.sample}</td>
                    <td>{formatValue(sample.median_intensity)}</td>
                    <td>{formatValue(sample.min_intensity)}</td>
                    <td>{formatValue(sample.max_intensity)}</td>
                    <td>{formatPercent(sample.missing_fraction)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {organismBreakdown.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Proteins by organism</h2>
          <div className={styles.dataTableWrap}>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>Organism</th>
                  <th>Proteins</th>
                </tr>
              </thead>
              <tbody>
                {organismBreakdown.map((item) => (
                  <tr key={item.organism}>
                    <td>{item.organism}</td>
                    <td>{formatValue(item.proteins)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {columnExplanations.length > 0 && (
        <section className={styles.section}>
          <details className={styles.explanationPanel}>
            <summary className={styles.explanationPanelSummary}>
              What the important columns mean
            </summary>
            <div className={styles.explanationList}>
              {columnExplanations.map((item) => (
                <div key={item.column} className={styles.explanationItem}>
                  <strong>{item.column}</strong>
                  <p>{item.explanation}</p>
                </div>
              ))}
            </div>
          </details>
        </section>
      )}

      {tablePreview?.columns?.length > 0 && (
        <section className={styles.section}>
          <div className={styles.tableHeader}>
            <h2 className={styles.sectionTitle}>Protein table</h2>
            <p className={styles.sectionMeta}>
              {rangeLabel}
              {hasActiveFilter ? ` (filtered from ${tablePreview.total_rows})` : ''}
            </p>
          </div>
          <div className={styles.dataTableWrap}>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  {tablePreview.columns.map((column) => (
                    <th key={column}>
                      <button
                        type="button"
                        className={styles.columnHeaderButton}
                        onClick={() => toggleColumnSort(column, sortColumn, sortDirection, setSortColumn, setSortDirection)}
                      >
                        <span className={styles.columnHeaderLabel}>{column}</span>
                        <span>{getSortIndicator(column, sortColumn, sortDirection)}</span>
                      </button>
                    </th>
                  ))}
                </tr>
                <tr>
                  {tableColumns.map((column) => (
                    <th key={`${column}-filter`} className={styles.filterHeaderCell}>
                      <input
                        type="search"
                        className={styles.columnFilterInput}
                        value={columnFilters[column] ?? ''}
                        onChange={(event) =>
                          setColumnFilters((currentFilters) => ({
                            ...currentFilters,
                            [column]: event.target.value,
                          }))
                        }
                        placeholder={`Filter ${column}`}
                        aria-label={`Filter ${column}`}
                      />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredAndSortedRows.map((row, rowIndex) => (
                  <tr key={buildTableRowKey(row, rowIndex, tableColumns)}>
                    {tableColumns.map((column) => (
                      <td key={`${rowIndex}-${column}`}>{formatTableCell(row[column])}</td>
                    ))}
                  </tr>
                ))}
                {filteredAndSortedRows.length === 0 && (
                  <tr>
                    <td colSpan={tableColumns.length} className={styles.emptyTableState}>
                      No proteins match the current column filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {typeof feedback === 'string' && feedback.trim().length > 0 && (
        <div className={styles.recommendationBox}>
          <strong>What to look for</strong>
          {renderTextOrHtml(feedback, styles.recommendationText)}
        </div>
      )}

      {recommendation && (
        <div className={styles.recommendationBox}>
          <strong>💡 Recommendation:</strong>
          <p className={styles.recommendationText}>{recommendation}</p>
        </div>
      )}

      {resultImages.length > 0 && (
        <div className={styles.imageSection}>
          <h2 className={styles.imageTitle}>Result Plots</h2>
          <div className={styles.imageGrid}>
            {resultImages.map((imageSrc, index) => (
              <figure
                key={index}
                className={styles.imageCard}
                onClick={() => onImageClick && onImageClick(index)}
                role={onImageClick ? 'button' : undefined}
                tabIndex={onImageClick ? 0 : undefined}
                onKeyDown={(e) => {
                  if (onImageClick && (e.key === 'Enter' || e.key === ' ')) {
                    e.preventDefault();
                    onImageClick(index);
                  }
                }}
              >
                <img
                  src={toImageDataUrl(imageSrc)}
                  alt={`Result plot ${index + 1}`}
                  className={styles.resultImage}
                />
                {onImageClick && <div className={styles.imageHint}>Click to enlarge</div>}
              </figure>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function normalizeImageList(imgValue) {
  if (Array.isArray(imgValue)) {
    return imgValue.filter((value) => typeof value === 'string' && value.trim().length > 0);
  }
  if (typeof imgValue === 'object' && imgValue !== null) {
    return Object.values(imgValue).filter(
      (value) => typeof value === 'string' && value.trim().length > 0
    );
  }
  if (typeof imgValue === 'string' && imgValue.trim().length > 0) {
    return [imgValue];
  }
  return [];
}

function toImageDataUrl(value) {
  return value.startsWith('data:image/') ? value : `data:image/png;base64,${value}`;
}

function renderTextOrHtml(value, className) {
  const trimmedValue = value.trim();
  const containsHtmlTag = /<\/?[a-z][\s\S]*>/i.test(trimmedValue);

  if (containsHtmlTag) {
    return <div className={className} dangerouslySetInnerHTML={{ __html: trimmedValue }} />;
  }

  return <p className={className}>{value}</p>;
}

function formatKey(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') return '—';
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'object' && value !== null) return JSON.stringify(value);
  return String(value);
}

function formatPercent(value) {
  if (value === null || value === undefined || value === '') return '—';
  return `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
}

function formatTableCell(value) {
  if (typeof value === 'number') {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return formatValue(value);
}

function buildTableRowKey(row, rowIndex, columns) {
  const preferredKey = TABLE_ROW_KEY_COLUMNS
    .map((column) => row[column])
    .find((value) => value !== null && value !== undefined && value !== '');

  if (preferredKey) {
    return `${preferredKey}-${rowIndex}`;
  }

  const firstPopulatedColumn = columns.find(
    (column) => row[column] !== null && row[column] !== undefined && row[column] !== ''
  );
  if (firstPopulatedColumn) {
    return `${row[firstPopulatedColumn]}-${rowIndex}`;
  }

  return `row-${rowIndex}`;
}

function getTableCellSearchText(value) {
  if (value === null || value === undefined) {
    return '';
  }
  if (Array.isArray(value)) {
    return value.join(' ').toLowerCase();
  }
  if (typeof value === 'object') {
    return JSON.stringify(value).toLowerCase();
  }
  return String(value).toLowerCase();
}

function compareTableValues(leftValue, rightValue) {
  if (leftValue === rightValue) {
    return 0;
  }
  if (leftValue === null || leftValue === undefined || leftValue === '') {
    return 1;
  }
  if (rightValue === null || rightValue === undefined || rightValue === '') {
    return -1;
  }

  const leftNumber = Number(leftValue);
  const rightNumber = Number(rightValue);
  const bothNumeric = Number.isFinite(leftNumber) && Number.isFinite(rightNumber);
  if (bothNumeric) {
    return leftNumber - rightNumber;
  }

  return String(leftValue).localeCompare(String(rightValue), undefined, {
    numeric: true,
    sensitivity: 'base',
  });
}

function toggleColumnSort(column, sortColumn, sortDirection, setSortColumn, setSortDirection) {
  if (sortColumn !== column) {
    setSortColumn(column);
    setSortDirection('asc');
    return;
  }

  setSortDirection((currentDirection) => (currentDirection === 'asc' ? 'desc' : 'asc'));
}

function getSortIndicator(column, sortColumn, sortDirection) {
  if (sortColumn !== column) {
    return '↕';
  }

  return sortDirection === 'asc' ? '↑' : '↓';
}
