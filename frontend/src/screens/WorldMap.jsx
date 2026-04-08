import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useGameStore from '../store/gameSlice';
import {
  WIDTH,
  HEIGHT,
  PLAYER_START,
  STATIONS,
  MOVE_KEYS,
  canMove,
  getNearbyStation,
  getStationAtTile,
  fitCanvasToViewport,
  pointerToTile,
  renderWorld,
} from './MapSetup';
import styles from './WorldMap.module.css';

export default function WorldMap() {
  const navigate = useNavigate();
  const completedStations = useGameStore((s) => s.completedStations);
  const canvasRef = useRef(null);
  const [player, setPlayer] = useState(PLAYER_START);

  const completedSet = useMemo(() => new Set(completedStations), [completedStations]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    const context = canvas.getContext('2d');
    if (!context) return undefined;

    canvas.width = WIDTH;
    canvas.height = HEIGHT;

    function fitCanvas() {
      fitCanvasToViewport(canvas);
    }

    fitCanvas();
    window.addEventListener('resize', fitCanvas);

    let rafId;

    function drawScene() {
      renderWorld(context, player, completedSet);

      rafId = window.requestAnimationFrame(drawScene);
    }

    drawScene();

    return () => {
      window.cancelAnimationFrame(rafId);
      window.removeEventListener('resize', fitCanvas);
    };
  }, [completedSet, player]);

  useEffect(() => {
    function handleKeyDown(event) {
      const key = event.key.toLowerCase();

      if (key === 'e' || key === 'enter') {
        const station = getNearbyStation(player.col, player.row);
        if (station) navigate(`/station/${station.id}`);
        return;
      }

      const delta = MOVE_KEYS[key];
      if (!delta) return;

      event.preventDefault();

      setPlayer((prev) => {
        const nextCol = prev.col + delta[0];
        const nextRow = prev.row + delta[1];
        return canMove(nextCol, nextRow) ? { col: nextCol, row: nextRow } : prev;
      });
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate, player.col, player.row]);

  function handleCanvasClick(event) {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const { col, row } = pointerToTile(canvas, event.clientX, event.clientY);

    const station = getStationAtTile(col, row);
    if (station) {
      navigate(`/station/${station.id}`);
      return;
    }

    if (canMove(col, row)) {
      setPlayer({ col, row });
    }
  }

  const nearbyStation = getNearbyStation(player.col, player.row);

  return (
    <div className={styles.page}>
      <div className={styles.headerRow}>
        <h1 className={styles.title}>Proteomics Lab Map</h1>
        <p className={styles.help}>Move: WASD or arrow keys | Enter station: E or Enter</p>
      </div>

      <div className={styles.canvasFrame}>
        <canvas
          ref={canvasRef}
          className={styles.canvas}
          onClick={handleCanvasClick}
          role="img"
          aria-label="2D world map"
        />
      </div>

      <div className={styles.statusRow}>
        <p className={styles.statusText}>
          Player tile: ({player.col}, {player.row})
        </p>
        <p className={styles.statusText}>
          Nearby station: {nearbyStation ? nearbyStation.label : 'None'}
        </p>
      </div>

      <div className={styles.legend}>
        {STATIONS.map((station) => {
          const done = completedSet.has(station.id);
          return (
            <button
              key={station.id}
              className={`${styles.stationButton} ${done ? styles.done : ''}`}
              onClick={() => navigate(`/station/${station.id}`)}
            >
              <span className={styles.swatch} style={{ backgroundColor: station.color }} />
              <span>{station.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
