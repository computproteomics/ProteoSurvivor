import { useEffect, useMemo, useState } from 'react';
import styles from './StationResults.module.css';

export function getStationResultsRenderer(_stationId, handlers = {}) {
  const { onImageClick } = handlers;

  return (props) => GenericStationResultsContent({ ...props, onImageClick });
}

function GenericStationResultsContent({
  stationResults,
  onImageClick,
  datasetView,
  datasetLoading,
  datasetError,
}) {
  const { summary, recommendation, feedback, img, ...detailFields } = stationResults;
  const resultImages = normalizeImageList(img);
  const hasDatasetTab = datasetLoading || Boolean(datasetError) || Boolean(datasetView?.available);
  const [activeTab, setActiveTab] = useState('details');

  useEffect(() => {
    if (!hasDatasetTab && activeTab !== 'details') {
      setActiveTab('details');
    }
  }, [activeTab, hasDatasetTab]);

  return (
    <>
      {hasDatasetTab && (
        <div className={styles.tabRow} role="tablist" aria-label="Station result tabs">
          <button
            className={`${styles.tabButton} ${activeTab === 'details' ? styles.activeTabButton : ''}`}
            onClick={() => setActiveTab('details')}
            type="button"
            role="tab"
            aria-selected={activeTab === 'details'}
          >
            Result details
          </button>
          <button
            className={`${styles.tabButton} ${activeTab === 'dataset' ? styles.activeTabButton : ''}`}
            onClick={() => setActiveTab('dataset')}
            type="button"
            role="tab"
            aria-selected={activeTab === 'dataset'}
          >
            Dataset table
          </button>
        </div>
      )}

      {activeTab === 'details' && (
        <>
          {summary && (
            <div className={styles.summaryBox}>
              <p className={styles.summaryText}>{summary}</p>
            </div>
          )}

          {Object.keys(detailFields).length > 0 && (
            <table className={styles.table}>
              <tbody>
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
      )}

      {activeTab === 'dataset' && (
        <DatasetBrowser
          datasetView={datasetView}
          datasetLoading={datasetLoading}
          datasetError={datasetError}
        />
      )}
    </>
  );
}

function DatasetBrowser({ datasetView, datasetLoading, datasetError }) {
  const [filterText, setFilterText] = useState('');
  const [sortConfig, setSortConfig] = useState({ column: null, direction: 'asc' });
  const [page, setPage] = useState(1);
  const columns = datasetView?.columns ?? [];
  const rows = datasetView?.rows ?? [];
  const importantColumns = datasetView?.important_columns ?? [];
  const pageSize = 50;

  const filteredRows = useMemo(() => {
    const normalizedFilter = filterText.trim().toLowerCase();
    if (!normalizedFilter) {
      return rows;
    }

    return rows.filter((row) =>
      columns.some((column) => String(row[column] ?? '').toLowerCase().includes(normalizedFilter))
    );
  }, [columns, filterText, rows]);

  const sortedRows = useMemo(() => {
    if (!sortConfig.column) {
      return filteredRows;
    }

    const nextRows = [...filteredRows];
    nextRows.sort((leftRow, rightRow) =>
      compareTableValues(leftRow[sortConfig.column], rightRow[sortConfig.column], sortConfig.direction)
    );
    return nextRows;
  }, [filteredRows, sortConfig]);

  const totalPages = Math.max(1, Math.ceil(sortedRows.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const visibleRows = sortedRows.slice((safePage - 1) * pageSize, safePage * pageSize);

  useEffect(() => {
    setPage(1);
  }, [datasetView?.row_count, filterText, sortConfig.column, sortConfig.direction]);

  if (datasetLoading) {
    return <p className={styles.datasetMessage}>Loading dataset table…</p>;
  }

  if (datasetError) {
    return <p className={styles.datasetMessage}>{datasetError}</p>;
  }

  if (!datasetView?.available) {
    return <p className={styles.datasetMessage}>No dataset is available for this station yet.</p>;
  }

  return (
    <div className={styles.datasetSection}>
      {importantColumns.length > 0 && (
        <details className={styles.columnGuide}>
          <summary className={styles.columnGuideSummary}>What the important columns mean</summary>
          <div className={styles.columnGuideBody}>
            {importantColumns.map((column) => (
              <div key={column.name} className={styles.columnGuideItem}>
                <strong>{column.name}</strong>
                <p>{column.description}</p>
              </div>
            ))}
          </div>
        </details>
      )}

      <div className={styles.tableToolbar}>
        <label className={styles.filterField}>
          <span>Filter rows</span>
          <input
            type="search"
            value={filterText}
            onChange={(event) => setFilterText(event.target.value)}
            placeholder="Search any value…"
            className={styles.filterInput}
          />
        </label>
        <p className={styles.tableSummary}>
          Showing {visibleRows.length} of {sortedRows.length} rows
          {sortedRows.length !== datasetView.row_count ? ` (filtered from ${datasetView.row_count})` : ''}
        </p>
      </div>

      <div className={styles.dataTableWrap}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>
                  <button
                    type="button"
                    className={styles.sortButton}
                    onClick={() => setSortConfig(nextSortConfig(sortConfig, column))}
                  >
                    <span>{column}</span>
                    <span className={styles.sortIndicator}>{getSortIndicator(sortConfig, column)}</span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, index) => (
              <tr key={`${safePage}-${index}`} className={styles.row}>
                {columns.map((column) => (
                  <td key={column} className={styles.dataValue}>
                    {formatDatasetCell(row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className={styles.paginationRow}>
        <button
          type="button"
          className={styles.secondaryButton}
          onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
          disabled={safePage === 1}
        >
          ← Previous page
        </button>
        <span className={styles.paginationInfo}>
          Page {safePage} of {totalPages}
        </span>
        <button
          type="button"
          className={styles.secondaryButton}
          onClick={() => setPage((currentPage) => Math.min(totalPages, currentPage + 1))}
          disabled={safePage === totalPages}
        >
          Next page →
        </button>
      </div>
    </div>
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
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'object' && value !== null) return JSON.stringify(value);
  return String(value);
}

function formatDatasetCell(value) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toLocaleString() : value.toPrecision(5);
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  return String(value);
}

function nextSortConfig(currentConfig, column) {
  if (currentConfig.column !== column) {
    return { column, direction: 'asc' };
  }

  return {
    column,
    direction: currentConfig.direction === 'asc' ? 'desc' : 'asc',
  };
}

function getSortIndicator(sortConfig, column) {
  if (sortConfig.column !== column) {
    return '↕';
  }

  return sortConfig.direction === 'asc' ? '↑' : '↓';
}

function compareTableValues(leftValue, rightValue, direction) {
  if (leftValue == null && rightValue == null) {
    return 0;
  }
  if (leftValue == null) {
    return 1;
  }
  if (rightValue == null) {
    return -1;
  }

  if (typeof leftValue === 'number' && typeof rightValue === 'number') {
    return direction === 'asc' ? leftValue - rightValue : rightValue - leftValue;
  }

  const leftText = String(leftValue).toLowerCase();
  const rightText = String(rightValue).toLowerCase();
  const comparison = leftText.localeCompare(rightText, undefined, { numeric: true });
  return direction === 'asc' ? comparison : -comparison;
}
