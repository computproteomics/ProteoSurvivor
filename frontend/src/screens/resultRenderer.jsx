import { useEffect, useMemo, useState } from 'react';
import styles from './StationResults.module.css';

const TABLE_ROW_KEY_COLUMNS = ['Protein ID', 'Protein', 'Gene'];
const TABLE_PAGE_SIZE = 25;

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
  const tableColumnIndex = useMemo(
    () => Object.fromEntries(tableColumns.map((column, index) => [column, index])),
    [tableColumns]
  );
  const numericColumns = useMemo(
    () =>
      Object.fromEntries(
        tableColumns.map((column) => [
          column,
          isNumericTableColumn(column, tableRows, tableColumnIndex),
        ])
      ),
    [tableColumnIndex, tableColumns, tableRows]
  );
  const [columnFilters, setColumnFilters] = useState({});
  const [sortColumn, setSortColumn] = useState('');
  const [sortDirection, setSortDirection] = useState('asc');
  const [currentPage, setCurrentPage] = useState(1);

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
        tableColumns.map((column) => {
          const currentFilter = currentFilters[column];
          if (numericColumns[column]) {
            const numericFilter =
              typeof currentFilter === 'object' && currentFilter !== null
                ? currentFilter
                : { min: '', max: '' };
            return [
              column,
              {
                min: numericFilter.min ?? '',
                max: numericFilter.max ?? '',
              },
            ];
          }

          return [column, typeof currentFilter === 'string' ? currentFilter : ''];
        })
      )
    );
  }, [numericColumns, tableColumns]);

  const activeTextColumnFilters = useMemo(
    () =>
      Object.fromEntries(
        tableColumns
          .filter((column) => !numericColumns[column])
          .map((column) => [column, (columnFilters[column] ?? '').trim().toLowerCase()])
          .filter(([, filterValue]) => filterValue.length > 0)
      ),
    [columnFilters, numericColumns, tableColumns]
  );

  const activeNumericColumnFilters = useMemo(
    () =>
      Object.fromEntries(
        tableColumns
          .filter((column) => numericColumns[column])
          .map((column) => {
            const filterValue = columnFilters[column];
            const min =
              typeof filterValue === 'object' && filterValue !== null
                ? normalizeRangeBoundary(filterValue.min)
                : null;
            const max =
              typeof filterValue === 'object' && filterValue !== null
                ? normalizeRangeBoundary(filterValue.max)
                : null;
            return [column, { min, max }];
          })
          .filter(([, filterValue]) => filterValue.min !== null || filterValue.max !== null)
      ),
    [columnFilters, numericColumns, tableColumns]
  );

  const filteredAndSortedRows = useMemo(() => {
    const filteredRows =
      Object.keys(activeTextColumnFilters).length === 0 &&
      Object.keys(activeNumericColumnFilters).length === 0
        ? tableRows
        : tableRows.filter((row) =>
            Object.entries(activeTextColumnFilters).every(([column, filterValue]) =>
              getTableCellSearchText(getTableValue(row, column, tableColumnIndex)).includes(filterValue)
            ) &&
            Object.entries(activeNumericColumnFilters).every(([column, filterValue]) =>
              doesTableValueMatchRange(
                getTableValue(row, column, tableColumnIndex),
                filterValue.min,
                filterValue.max
              )
            )
          );

    if (!sortColumn) {
      return filteredRows;
    }

    return [...filteredRows].sort((leftRow, rightRow) => {
      const comparison = compareTableValues(
        getTableValue(leftRow, sortColumn, tableColumnIndex),
        getTableValue(rightRow, sortColumn, tableColumnIndex)
      );
      return sortDirection === 'desc' ? comparison * -1 : comparison;
    });
  }, [
    activeNumericColumnFilters,
    activeTextColumnFilters,
    sortColumn,
    sortDirection,
    tableColumnIndex,
    tableRows,
  ]);

  const renderedTableRows = useMemo(
    () =>
      filteredAndSortedRows.map((row, rowIndex) => ({
        key: buildTableRowKey(row, rowIndex, tableColumns, tableColumnIndex),
        row,
      })),
    [filteredAndSortedRows, tableColumnIndex, tableColumns]
  );

  const totalFilteredRows = filteredAndSortedRows.length;
  const totalRows = tablePreview?.total_rows ?? tableRows.length;
  const hasActiveFilter =
    Object.keys(activeTextColumnFilters).length > 0 ||
    Object.keys(activeNumericColumnFilters).length > 0;
  const totalPages = Math.max(1, Math.ceil(totalFilteredRows / TABLE_PAGE_SIZE));
  const pageStartIndex = totalFilteredRows === 0 ? 0 : (currentPage - 1) * TABLE_PAGE_SIZE;
  const pageEndIndex = Math.min(pageStartIndex + TABLE_PAGE_SIZE, totalFilteredRows);
  const pagedTableRows = useMemo(
    () => renderedTableRows.slice(pageStartIndex, pageEndIndex),
    [pageEndIndex, pageStartIndex, renderedTableRows]
  );
  const rangeLabel =
    totalFilteredRows === 0
      ? 'Showing 0 rows'
      : `Showing rows ${pageStartIndex + 1}-${pageEndIndex} of ${totalFilteredRows}`;

  useEffect(() => {
    setCurrentPage(1);
  }, [activeNumericColumnFilters, activeTextColumnFilters, tableRows]);

  useEffect(() => {
    setCurrentPage((page) => Math.min(page, totalPages));
  }, [totalPages]);

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
              {hasActiveFilter ? ` (filtered from ${totalRows})` : ''}
              {totalFilteredRows > 0 ? ` • Page ${currentPage} of ${totalPages}` : ''}
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
                      {numericColumns[column] ? (
                        <div className={styles.rangeFilterInputs}>
                          <input
                            type="number"
                            inputMode="decimal"
                            className={styles.columnFilterInput}
                            value={columnFilters[column]?.min ?? ''}
                            onChange={(event) =>
                              setColumnFilters((currentFilters) => ({
                                ...currentFilters,
                                [column]: {
                                  min: event.target.value,
                                  max: currentFilters[column]?.max ?? '',
                                },
                              }))
                            }
                            placeholder="Min"
                            aria-label={`Minimum ${column}`}
                          />
                          <input
                            type="number"
                            inputMode="decimal"
                            className={styles.columnFilterInput}
                            value={columnFilters[column]?.max ?? ''}
                            onChange={(event) =>
                              setColumnFilters((currentFilters) => ({
                                ...currentFilters,
                                [column]: {
                                  min: currentFilters[column]?.min ?? '',
                                  max: event.target.value,
                                },
                              }))
                            }
                            placeholder="Max"
                            aria-label={`Maximum ${column}`}
                          />
                        </div>
                      ) : (
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
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pagedTableRows.map(({ key, row }) => (
                  <tr key={key}>
                    {tableColumns.map((column) => (
                      <td key={`${key}-${column}`}>{formatTableCell(getTableValue(row, column, tableColumnIndex))}</td>
                    ))}
                  </tr>
                ))}
                {pagedTableRows.length === 0 && (
                  <tr>
                    <td colSpan={tableColumns.length} className={styles.emptyTableState}>
                      No proteins match the current column filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {totalFilteredRows > TABLE_PAGE_SIZE && (
            <div className={styles.paginationBar}>
              <label className={styles.pageSelectLabel}>
                Page
                <select
                  className={styles.pageSelect}
                  value={currentPage}
                  onChange={(event) => setCurrentPage(Number(event.target.value))}
                  aria-label="Select table page"
                >
                  {Array.from({ length: totalPages }, (_, index) => index + 1).map((pageNumber) => (
                    <option key={pageNumber} value={pageNumber}>
                      {pageNumber}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                disabled={currentPage === 1}
              >
                ← Previous
              </button>
              <span className={styles.paginationInfo}>
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                disabled={currentPage === totalPages}
              >
                Next →
              </button>
            </div>
          )}
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

function getTableValue(row, column, columnIndex) {
  if (Array.isArray(row)) {
    const valueIndex = columnIndex[column];
    return valueIndex === undefined ? undefined : row[valueIndex];
  }

  if (typeof row === 'object' && row !== null) {
    return row[column];
  }

  return undefined;
}

function buildTableRowKey(row, rowIndex, columns, columnIndex) {
  const preferredKey = TABLE_ROW_KEY_COLUMNS
    .map((column) => getTableValue(row, column, columnIndex))
    .find((value) => value !== null && value !== undefined && value !== '');

  if (preferredKey) {
    return `${preferredKey}-${rowIndex}`;
  }

  const firstPopulatedColumn = columns.find(
    (column) => {
      const value = getTableValue(row, column, columnIndex);
      return value !== null && value !== undefined && value !== '';
    }
  );
  if (firstPopulatedColumn) {
    return `${getTableValue(row, firstPopulatedColumn, columnIndex)}-${rowIndex}`;
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

function normalizeRangeBoundary(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

function doesTableValueMatchRange(value, min, max) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return false;
  }

  if (min !== null && numericValue < min) {
    return false;
  }

  if (max !== null && numericValue > max) {
    return false;
  }

  return true;
}

function isNumericTableColumn(column, rows, columnIndex) {
  let sawNumericValue = false;

  for (const row of rows) {
    const value = getTableValue(row, column, columnIndex);
    if (value === null || value === undefined || value === '') {
      continue;
    }
    if (typeof value === 'boolean') {
      return false;
    }

    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) {
      return false;
    }

    sawNumericValue = true;
  }

  return sawNumericValue;
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
