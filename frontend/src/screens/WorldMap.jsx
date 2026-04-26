import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useGameStore from '../store/gameSlice';
import {
  WIDTH,
  HEIGHT,
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

const CLICK_WALK_STEP_MS = 130;
const WALK_NEIGHBORS = [
  { dc: 0, dr: -1, direction: 0 },
  { dc: 1, dr: 0, direction: 1 },
  { dc: 0, dr: 1, direction: 2 },
  { dc: -1, dr: 0, direction: 3 },
];

function keyFor(col, row) {
  return `${col},${row}`;
}

function findPath(start, target) {
  const startKey = keyFor(start.col, start.row);
  const targetKey = keyFor(target.col, target.row);

  if (startKey === targetKey) {
    return [];
  }

  const queue = [start];
  const visited = new Set([startKey]);
  const parentByKey = new Map();

  while (queue.length > 0) {
    const current = queue.shift();
    const currentKey = keyFor(current.col, current.row);

    for (const { dc, dr } of WALK_NEIGHBORS) {
      const nextCol = current.col + dc;
      const nextRow = current.row + dr;
      const nextKey = keyFor(nextCol, nextRow);

      if (visited.has(nextKey) || !canMove(nextCol, nextRow)) {
        continue;
      }

      visited.add(nextKey);
      parentByKey.set(nextKey, currentKey);

      if (nextKey === targetKey) {
        const path = [];
        let walkKey = nextKey;

        while (walkKey !== startKey) {
          const [colString, rowString] = walkKey.split(',');
          path.push({ col: Number(colString), row: Number(rowString) });
          walkKey = parentByKey.get(walkKey);
        }

        path.reverse();
        return path;
      }

      queue.push({ col: nextCol, row: nextRow });
    }
  }

  return null;
}

function findStationApproachPath(start, station) {
  const approachTiles = WALK_NEIGHBORS
    .map(({ dc, dr }) => ({ col: station.col + dc, row: station.row + dr }))
    .filter((tile) => canMove(tile.col, tile.row));

  let bestPath = null;
  for (const tile of approachTiles) {
    const path = findPath(start, tile);
    if (!path) continue;
    if (!bestPath || path.length < bestPath.length) {
      bestPath = path;
    }
  }

  return bestPath;
}

export default function WorldMap() {
  const navigate = useNavigate();
  const completedStations = useGameStore((s) => s.completedStations);
  const player = useGameStore((s) => s.mapPlayerPosition);
  const setMapPlayerPosition = useGameStore((s) => s.setMapPlayerPosition);
  const canvasRef = useRef(null);
  const clickWalkPathRef = useRef([]);
  const clickWalkTimerRef = useRef(null);
  const clickWalkArrivalActionRef = useRef(null);
  const [animState, setAnimState] = useState({
    isMoving: false,
    direction: 2, // 0=up, 1=right, 2=down, 3=left
    frameIndex: 0,
    lastUpdate: 0,
  });

  const completedSet = useMemo(() => new Set(completedStations), [completedStations]);

  function stopClickWalk() {
    clickWalkPathRef.current = [];
    clickWalkArrivalActionRef.current = null;
    if (clickWalkTimerRef.current) {
      clearInterval(clickWalkTimerRef.current);
      clickWalkTimerRef.current = null;
    }
    setAnimState((prev) => ({ ...prev, isMoving: false, frameIndex: 0 }));
  }

  function startClickWalk(path, onArrival) {
    stopClickWalk();

    clickWalkArrivalActionRef.current = onArrival || null;

    if (!path || path.length === 0) {
      if (clickWalkArrivalActionRef.current) {
        clickWalkArrivalActionRef.current();
        clickWalkArrivalActionRef.current = null;
      }
      return;
    }

    clickWalkPathRef.current = [...path];
    setAnimState((prev) => ({ ...prev, isMoving: true }));

    clickWalkTimerRef.current = setInterval(() => {
      setMapPlayerPosition((prevPos) => {
        const nextPos = clickWalkPathRef.current.shift();

        if (!nextPos) {
          return prevPos;
        }

        const dc = nextPos.col - prevPos.col;
        const dr = nextPos.row - prevPos.row;
        const nextDirection = WALK_NEIGHBORS.find((neighbor) => neighbor.dc === dc && neighbor.dr === dr);

        if (nextDirection) {
          setAnimState((prevAnim) => ({
            ...prevAnim,
            isMoving: true,
            direction: nextDirection.direction,
          }));
        }

        if (clickWalkPathRef.current.length === 0) {
          setTimeout(() => {
            setAnimState((prevAnim) => ({ ...prevAnim, isMoving: false, frameIndex: 0 }));
          }, CLICK_WALK_STEP_MS / 2);

          if (clickWalkArrivalActionRef.current) {
            clickWalkArrivalActionRef.current();
            clickWalkArrivalActionRef.current = null;
          }

          if (clickWalkTimerRef.current) {
            clearInterval(clickWalkTimerRef.current);
            clickWalkTimerRef.current = null;
          }
        }

        return nextPos;
      });
    }, CLICK_WALK_STEP_MS);
  }

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
    return () => {
      if (clickWalkTimerRef.current) {
        clearInterval(clickWalkTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    function handleKeyDown(event) {
      const key = event.key.toLowerCase();

      stopClickWalk();

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
      const approachPath = findStationApproachPath(player, station);
      if (approachPath) {
        startClickWalk(approachPath, () => navigate(`/station/${station.id}`));
      }
      return;
    }

    if (canMove(col, row)) {
      const path = findPath(player, { col, row });
      if (path && path.length > 0) {
        startClickWalk(path);
      }
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
        <button className={styles.creditsButton} onClick={() => navigate('/credits')}>
          Credits
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
