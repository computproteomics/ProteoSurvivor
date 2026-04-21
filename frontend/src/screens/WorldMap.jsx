import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useGameStore from '../store/gameSlice';
import {
  WIDTH,
  HEIGHT,
  STATIONS,
  MOVE_KEYS,
  KEY_TO_DIRECTION,
  canMove,
  getNearbyStation,
  getStationAtTile,
  fitCanvasToViewport,
  loadSprites,
  pointerToTile,
  renderWorld,
  updateAnimation,
} from './MapSetup';
import styles from './WorldMap.module.css';

export default function WorldMap() {
  const navigate = useNavigate();
  const completedStations = useGameStore((s) => s.completedStations);
  const player = useGameStore((s) => s.mapPlayerPosition);
  const setMapPlayerPosition = useGameStore((s) => s.setMapPlayerPosition);
  const canvasRef = useRef(null);
  const [animState, setAnimState] = useState({
    isMoving: false,
    direction: 2, // 0=up, 1=right, 2=down, 3=left
    frameIndex: 0,
    lastUpdate: 0,
  });

  const completedSet = useMemo(() => new Set(completedStations), [completedStations]);
  const mapOrderedStations = useMemo(
    () => [...STATIONS].sort((a, b) => a.row - b.row || a.col - b.col),
    []
  );

  useEffect(() => {
    loadSprites();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const context = canvas.getContext('2d');
    if (!context) return;

    canvas.width = WIDTH;
    canvas.height = HEIGHT;

    let animationFrame;

    function loop() {
      renderWorld(context, player, completedSet, animState);
      animationFrame = requestAnimationFrame(loop);
    }

    loop();

    function handleResize() {
      fitCanvasToViewport(canvas);
    }

    handleResize();
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrame);
      window.removeEventListener('resize', handleResize);
    };
  }, [player, completedSet, animState]);

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
      setMapPlayerPosition((prev) => {
        const nextCol = prev.col + delta[0];
        const nextRow = prev.row + delta[1];

        const moved = canMove(nextCol, nextRow);

        // Update animation state
        setAnimState((prevAnim) => ({
          ...prevAnim,
          isMoving: moved,
          direction: ['up', 'right', 'down', 'left'].indexOf(
            KEY_TO_DIRECTION[key]
          ),
        }));

        return moved ? { col: nextCol, row: nextRow } : prev;
      });
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate, player.col, player.row, setMapPlayerPosition]);

  useEffect(() => {
    let animationFrame;

    function loop(now) {
      setAnimState((prev) => updateAnimation(prev, now));
      animationFrame = requestAnimationFrame(loop);
    }

    animationFrame = requestAnimationFrame(loop);

    return () => cancelAnimationFrame(animationFrame);
  }, []);
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
      setMapPlayerPosition({ col, row });
    }
  }

  const nearbyStation = getNearbyStation(player.col, player.row);

  return (
    <div className={styles.page}>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.title}>Proteomics Lab Map</h1>
          <p className={styles.help}>Move: WASD or arrow keys | Enter station: E or Enter</p>
        </div>
        <button className={styles.leaderboardButton} onClick={() => navigate('/leaderboard')}>
          View leaderboard
        </button>
      </div>

      <div className={styles.mapContainer}>
        <div className={styles.legend}>
          <div className={styles.nearbyStationBox}>
            <p className={styles.nearbyLabel}>Nearby Station</p>
            <p className={styles.nearbyValue}>
              {nearbyStation ? nearbyStation.label : 'None'}
            </p>
          </div>

          <div className={styles.legendSpacer} />

          {mapOrderedStations.map((station) => {
            const done = completedSet.has(station.id);
            return (
              <button
                key={station.id}
                className={`${styles.stationButton} ${done ? styles.done : ''}`}
                onClick={() => navigate(`/station/${station.id}`)}
              >
                <span className={styles.swatch} style={{ backgroundColor: station.color }} />
                <span className={styles.buttonLabel}>{station.label}</span>
              </button>
            );
          })}
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
      </div>
    </div>
  );
}
