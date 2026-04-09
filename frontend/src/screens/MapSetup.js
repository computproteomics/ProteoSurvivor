import { STATION_IDS, getStationTitle } from '../assets/stationConfig';

// Map Configuration
export const TILE = 48;
export const COLS = 22;
export const ROWS = 16;
export const WIDTH = COLS * TILE;
export const HEIGHT = ROWS * TILE;

// Player start position
export const PLAYER_START = { col: 2, row: 2 };

// Colors
export const COLORS = {
  floorA: '#d0dce8',
  floorB: '#c4d4e2',
  wall: '#3a5070',
  wallTop: '#4a6888',
  wallShadow: '#243448',
  bench: '#7a9ab8',
  benchTop: '#9ab8d0',
  player: '#1a2a3a',
  playerAccent: '#5ad4f8',
  ring: '#f8e45a',
};

// Map Layout
export const MAP = [
  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 2, 1],
  [1, 2, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 2, 1],
  [1, 2, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 2, 1],
  [1, 2, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 3, 3, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
];

const STATION_POSITIONS_BY_ID = {
  sample_prep: { col: 16, row: 3 },
  mass_spec: { col: 8, row: 3 },
  spectral_search: { col: 12, row: 6 },
  filtering: { col: 8, row: 6 },
  transform: { col: 8, row: 10 },
  normalize: { col: 4, row: 3 },
  imputer: { col: 12, row: 3 },
  multiple_testing_corrector: { col: 16, row: 6 },
  the_cutter: { col: 4, row: 10 },
  statistical_analysis: { col: 4, row: 6 },
  veit: { col: 12, row: 10 },
};

const STATION_COLORS = {
  sample_prep: '#f8b85a',
  mass_spec: '#5ad4f8',
  spectral_search: '#7dd3fc',
  filtering: '#f89d5a',
  transform: '#86efac',
  normalize: '#58c87a',
  imputer: '#b87af8',
  multiple_testing_corrector: '#c4b5fd',
  the_cutter: '#fca5a5',
  statistical_analysis: '#f86a6a',
  veit: '#fde68a',
};

// ── Station icon drawers ─────────────────────────────────────────────────────
// Each function draws a miniature canvas vector icon centred at (cx, cy).
// All internal coordinates are relative to that centre point and designed
// to fit inside the 24×24 inner tile square (±12 from centre).

// sample_prep: tilted test tube with liquid fill
function drawIconSamplePrep(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(-Math.PI / 5);
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = '#1f2937';
  ctx.beginPath();
  ctx.moveTo(-3, -9);
  ctx.lineTo(-3, 5);
  ctx.arc(0, 5, 3, Math.PI, 0);
  ctx.lineTo(3, -9);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-4, -9);
  ctx.lineTo(4, -9);
  ctx.stroke();
  ctx.fillStyle = 'rgba(255,255,255,0.55)';
  ctx.beginPath();
  ctx.moveTo(-2.5, 1);
  ctx.lineTo(-2.5, 5);
  ctx.arc(0, 5, 2.5, Math.PI, 0);
  ctx.lineTo(2.5, 1);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

// mass_spec: rectangular instrument body + inlet funnel + signal wave
function drawIconMassSpec(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = '#1f2937';
  ctx.strokeRect(-8, -4, 11, 8);
  ctx.beginPath();
  ctx.moveTo(-8, -2);
  ctx.lineTo(-11, -4);
  ctx.moveTo(-8, 2);
  ctx.lineTo(-11, 4);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(3, 0);
  ctx.lineTo(5, 0);
  ctx.lineTo(6, -4);
  ctx.lineTo(7, 4);
  ctx.lineTo(8, -4);
  ctx.lineTo(9, 0);
  ctx.lineTo(10, 0);
  ctx.stroke();
  ctx.restore();
}

// spectral_search: magnifying glass with spectral lines in the lens
function drawIconSpectralSearch(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineWidth = 1.8;
  ctx.strokeStyle = '#1f2937';
  ctx.beginPath();
  ctx.arc(-2, -2, 6, 0, Math.PI * 2);
  ctx.stroke();
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(3, 3);
  ctx.lineTo(8, 8);
  ctx.stroke();
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(-5, -2);
  ctx.lineTo(-4, -2);
  ctx.moveTo(-3, -2);
  ctx.lineTo(-1, -2);
  ctx.moveTo(0, -2);
  ctx.lineTo(1, -2);
  ctx.stroke();
  ctx.restore();
}

// filtering: funnel outline with three horizontal filter bars
function drawIconFiltering(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = '#1f2937';
  ctx.beginPath();
  ctx.moveTo(-9, -8);
  ctx.lineTo(9, -8);
  ctx.lineTo(2, 2);
  ctx.lineTo(2, 9);
  ctx.lineTo(-2, 9);
  ctx.lineTo(-2, 2);
  ctx.lineTo(-9, -8);
  ctx.stroke();
  ctx.lineWidth = 1;
  for (let i = 0; i < 3; i += 1) {
    const t = i / 2;
    const lx = -9 + t * 7;
    const rx = 9 - t * 7;
    const fy = -8 + t * 10;
    ctx.beginPath();
    ctx.moveTo(lx + 1.5, fy);
    ctx.lineTo(rx - 1.5, fy);
    ctx.stroke();
  }
  ctx.restore();
}

// transform: circular arrow with small molecule dot at centre
function drawIconTransform(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineWidth = 1.8;
  ctx.strokeStyle = '#1f2937';
  ctx.beginPath();
  ctx.arc(0, 0, 7, -Math.PI / 2, Math.PI, false);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(0, -7);
  ctx.lineTo(-4, -3);
  ctx.moveTo(0, -7);
  ctx.lineTo(3, -4);
  ctx.stroke();
  ctx.fillStyle = '#1f2937';
  ctx.beginPath();
  ctx.arc(0, 0, 2, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

// normalize: Gaussian bell curve with dashed mean line
function drawIconNormalize(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = '#1f2937';
  ctx.beginPath();
  ctx.moveTo(-10, 6);
  ctx.lineTo(10, 6);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-9, 6);
  ctx.bezierCurveTo(-6, 6, -5, -8, 0, -8);
  ctx.bezierCurveTo(5, -8, 6, 6, 9, 6);
  ctx.stroke();
  ctx.lineWidth = 1;
  ctx.setLineDash([2, 2]);
  ctx.beginPath();
  ctx.moveTo(0, -8);
  ctx.lineTo(0, 6);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();
}

// imputer: horizontal syringe with barrel, plunger, needle and graduation ticks
function drawIconImputer(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = '#1f2937';
  ctx.strokeRect(-6, -3, 10, 6);
  ctx.beginPath();
  ctx.moveTo(4, 0);
  ctx.lineTo(9, 0);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(7, -3);
  ctx.lineTo(7, 3);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-6, 0);
  ctx.lineTo(-10, 0);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-9, -1);
  ctx.lineTo(-11, 0);
  ctx.lineTo(-9, 1);
  ctx.stroke();
  ctx.lineWidth = 1;
  for (let i = 0; i < 3; i += 1) {
    ctx.beginPath();
    ctx.moveTo(-3 + i * 3, -3);
    ctx.lineTo(-3 + i * 3, 3);
    ctx.stroke();
  }
  ctx.restore();
}

// multiple_testing_corrector: bar chart with dashed significance threshold
function drawIconMTC(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = '#1f2937';
  ctx.beginPath();
  ctx.moveTo(-9, 8);
  ctx.lineTo(9, 8);
  ctx.stroke();
  [[-6, 11], [-1, 7], [4, 4]].forEach(([bx, h]) => {
    ctx.strokeRect(bx, 8 - h, 3, h);
  });
  ctx.setLineDash([2, 2]);
  ctx.strokeStyle = '#c0392b';
  ctx.beginPath();
  ctx.moveTo(-9, 1);
  ctx.lineTo(9, 1);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();
}

// the_cutter: scissors – two blade tips + handle rings + pivot
function drawIconCutter(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = '#1f2937';
  ctx.beginPath();
  ctx.arc(0, 0, 2.5, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(1.5, -1.5);
  ctx.lineTo(8, -7);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(8, -7, 2, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(1.5, 1.5);
  ctx.lineTo(8, 7);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(8, 7, 2, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-1.5, -1.5);
  ctx.lineTo(-7, -5);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(-7, -5, 3, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-1.5, 1.5);
  ctx.lineTo(-7, 5);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(-7, 5, 3, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

// statistical_analysis: volcano plot – V-shaped cutoff lines, dashed p-value
// threshold, red significant dots above and grey non-significant dots below
function drawIconStatAnalysis(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineWidth = 1;
  ctx.strokeStyle = '#1f2937';
  ctx.beginPath();
  ctx.moveTo(-9, 8);
  ctx.lineTo(9, 8);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-9, 8);
  ctx.lineTo(-4, -2);
  ctx.moveTo(9, 8);
  ctx.lineTo(4, -2);
  ctx.stroke();
  ctx.setLineDash([2, 2]);
  ctx.beginPath();
  ctx.moveTo(-9, -2);
  ctx.lineTo(9, -2);
  ctx.stroke();
  ctx.setLineDash([]);
  [[-6, -5], [7, -7], [-8, -8], [6, -4]].forEach(([dx, dy]) => {
    ctx.fillStyle = '#c0392b';
    ctx.beginPath();
    ctx.arc(dx, dy, 1.5, 0, Math.PI * 2);
    ctx.fill();
  });
  [[-1, 3], [2, 2], [0, 5], [-3, 4]].forEach(([dx, dy]) => {
    ctx.fillStyle = '#7f8c8d';
    ctx.beginPath();
    ctx.arc(dx, dy, 1, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.restore();
}

// veit: stick-figure person (head circle + torso + arms + legs)
function drawIconVeit(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = '#1f2937';
  ctx.beginPath();
  ctx.arc(0, -5, 3.5, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(0, -1.5);
  ctx.lineTo(0, 4);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-5, 1);
  ctx.lineTo(5, 1);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(0, 4);
  ctx.lineTo(-4, 9);
  ctx.moveTo(0, 4);
  ctx.lineTo(4, 9);
  ctx.stroke();
  ctx.restore();
}

const STATION_ICON_DRAWERS = {
  sample_prep: drawIconSamplePrep,
  mass_spec: drawIconMassSpec,
  spectral_search: drawIconSpectralSearch,
  filtering: drawIconFiltering,
  transform: drawIconTransform,
  normalize: drawIconNormalize,
  imputer: drawIconImputer,
  multiple_testing_corrector: drawIconMTC,
  the_cutter: drawIconCutter,
  statistical_analysis: drawIconStatAnalysis,
  veit: drawIconVeit,
};

// Station definitions with position on map and color
export const STATIONS = STATION_IDS.map((id) => ({
  id,
  label: getStationTitle(id),
  ...STATION_POSITIONS_BY_ID[id],
  color: STATION_COLORS[id],
}));

// Movement keys and their corresponding column/row deltas
export const MOVE_KEYS = {
  arrowup: [0, -1],
  w: [0, -1],
  arrowdown: [0, 1],
  s: [0, 1],
  arrowleft: [-1, 0],
  a: [-1, 0],
  arrowright: [1, 0],
  d: [1, 0],
};

// Returns true only for in-bounds, walkable tiles (not walls or benches).
export function canMove(col, row) {
  if (row < 0 || row >= ROWS || col < 0 || col >= COLS) return false;
  const tile = MAP[row][col];
  return tile !== 1 && tile !== 3;
}

// Uses Manhattan distance so a station is reachable from adjacent tiles.
export function getNearbyStation(playerCol, playerRow) {
  return STATIONS.find((station) => {
    const distance = Math.abs(station.col - playerCol) + Math.abs(station.row - playerRow);
    return distance <= 1;
  });
}

// Finds a station exactly on one tile, used for direct click-to-enter.
export function getStationAtTile(col, row) {
  return STATIONS.find((station) => station.col === col && station.row === row);
}

// Scales the logical canvas into the viewport while preserving aspect ratio.
export function fitCanvasToViewport(canvas) {
  const scale = Math.min((window.innerWidth * 0.9) / WIDTH, (window.innerHeight * 0.75) / HEIGHT);
  canvas.style.width = `${Math.floor(WIDTH * scale)}px`;
  canvas.style.height = `${Math.floor(HEIGHT * scale)}px`;
}

// Converts screen-space pointer coordinates to map tile coordinates.
export function pointerToTile(canvas, clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  // The canvas is visually scaled with CSS, so convert back to logical pixels.
  const scaleX = WIDTH / rect.width;
  const scaleY = HEIGHT / rect.height;
  const x = (clientX - rect.left) * scaleX;
  const y = (clientY - rect.top) * scaleY;

  return {
    col: Math.floor(x / TILE),
    row: Math.floor(y / TILE),
  };
}

// Draws one tile variant (wall, bench, or floor checker tile).
function drawTile(context, col, row, tileType) {
  const x = col * TILE;
  const y = row * TILE;

  if (tileType === 1) {
    // Layered rectangles give walls a simple top-light/shadow depth.
    context.fillStyle = COLORS.wallShadow;
    context.fillRect(x, y, TILE, TILE);
    context.fillStyle = COLORS.wall;
    context.fillRect(x + 2, y + 10, TILE - 2, TILE - 10);
    context.fillStyle = COLORS.wallTop;
    context.fillRect(x + 2, y + 2, TILE - 2, 10);
    return;
  }

  if (tileType === 3) {
    // Bench tiles are drawn on top of floor so they read as obstacles.
    context.fillStyle = COLORS.floorA;
    context.fillRect(x, y, TILE, TILE);
    context.fillStyle = COLORS.bench;
    context.fillRect(x + 6, y + 18, TILE - 12, TILE - 20);
    context.fillStyle = COLORS.benchTop;
    context.fillRect(x + 6, y + 8, TILE - 12, 12);
    return;
  }

  context.fillStyle = (row + col) % 2 === 0 ? COLORS.floorA : COLORS.floorB;
  context.fillRect(x, y, TILE, TILE);
}

// Draws a station marker and completion badge if it has been cleared.
function drawStation(context, station, done) {
  const x = station.col * TILE;
  const y = station.row * TILE;

  context.fillStyle = station.color;
  context.fillRect(x + 12, y + 12, TILE - 24, TILE - 24);

  context.strokeStyle = done ? '#1d8a4f' : '#1f2937';
  context.lineWidth = 3;
  context.strokeRect(x + 12, y + 12, TILE - 24, TILE - 24);

  // Draw station-specific canvas vector icon centred on the tile.
  const drawIcon = STATION_ICON_DRAWERS[station.id];
  if (drawIcon) {
    context.save();
    drawIcon(context, x + TILE / 2, y + TILE / 2);
    context.restore();
  }

  // Completion badge: green circle with drawn checkmark in the top-right corner.
  if (done) {
    context.save();
    context.fillStyle = '#1d8a4f';
    context.beginPath();
    context.arc(x + TILE - 10, y + 10, 8, 0, Math.PI * 2);
    context.fill();
    context.strokeStyle = '#ffffff';
    context.lineWidth = 2;
    context.lineCap = 'round';
    context.lineJoin = 'round';
    context.beginPath();
    context.moveTo(x + TILE - 14, y + 10);
    context.lineTo(x + TILE - 10, y + 14);
    context.lineTo(x + TILE - 6, y + 6);
    context.stroke();
    context.restore();
  }
}

// Draws the player and a ring around the nearest interactable station.
function drawPlayer(context, player) {
  const px = player.col * TILE;
  const py = player.row * TILE;

  context.fillStyle = COLORS.player;
  context.beginPath();
  context.arc(px + TILE / 2, py + TILE / 2, 12, 0, Math.PI * 2);
  context.fill();

  context.fillStyle = COLORS.playerAccent;
  context.beginPath();
  context.arc(px + TILE / 2 + 4, py + TILE / 2 - 4, 4, 0, Math.PI * 2);
  context.fill();

  const nearby = getNearbyStation(player.col, player.row);
  if (nearby) {
    context.strokeStyle = COLORS.ring;
    context.lineWidth = 3;
    context.beginPath();
    context.arc(nearby.col * TILE + TILE / 2, nearby.row * TILE + TILE / 2, 18, 0, Math.PI * 2);
    context.stroke();
  }
}

// Renders the whole world in draw order: terrain -> stations -> player.
export function renderWorld(context, player, completedSet) {
  context.clearRect(0, 0, WIDTH, HEIGHT);

  for (let row = 0; row < ROWS; row += 1) {
    for (let col = 0; col < COLS; col += 1) {
      drawTile(context, col, row, MAP[row][col]);
    }
  }

  STATIONS.forEach((station) => drawStation(context, station, completedSet.has(station.id)));
  drawPlayer(context, player);
}