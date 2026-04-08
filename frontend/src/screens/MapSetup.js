export const TILE = 48;
export const COLS = 22;
export const ROWS = 16;
export const WIDTH = COLS * TILE;
export const HEIGHT = ROWS * TILE;

export const PLAYER_START = { col: 2, row: 2 };

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

export const MAP = [
  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 3, 3, 3, 2, 2, 3, 3, 3, 2, 2, 3, 3, 3, 2, 2, 3, 3, 2, 1],
  [1, 2, 2, 3, 3, 3, 2, 2, 3, 3, 3, 2, 2, 3, 3, 3, 2, 2, 3, 3, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 3, 3, 3, 2, 2, 3, 3, 3, 2, 2, 3, 3, 3, 2, 2, 3, 3, 2, 1],
  [1, 2, 2, 3, 3, 3, 2, 2, 3, 3, 3, 2, 2, 3, 3, 3, 2, 2, 3, 3, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
];

export const STATIONS = [
  { id: 'sample_prep', label: 'Sample Preparation', col: 3, row: 3, color: '#58c87a' },
  { id: 'mass_spec', label: 'LC/MS-MS', col: 8, row: 3, color: '#5ad4f8' },
  { id: 'search_setup', label: 'Database Search', col: 13, row: 3, color: '#b87af8' },
  { id: 'data_analysis', label: 'Statistical Testing', col: 13, row: 10, color: '#f86a6a' },
  { id: 'veit', label: 'Veit', col: 18, row: 10, color: '#f8b85a' },
];

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

export function canMove(col, row) {
  if (row < 0 || row >= ROWS || col < 0 || col >= COLS) return false;
  const tile = MAP[row][col];
  return tile !== 1 && tile !== 3;
}

export function getNearbyStation(playerCol, playerRow) {
  return STATIONS.find((station) => {
    const distance = Math.abs(station.col - playerCol) + Math.abs(station.row - playerRow);
    return distance <= 1;
  });
}

export function getStationAtTile(col, row) {
  return STATIONS.find((station) => station.col === col && station.row === row);
}

export function fitCanvasToViewport(canvas) {
  const scale = Math.min((window.innerWidth * 0.9) / WIDTH, (window.innerHeight * 0.75) / HEIGHT);
  canvas.style.width = `${Math.floor(WIDTH * scale)}px`;
  canvas.style.height = `${Math.floor(HEIGHT * scale)}px`;
}

export function pointerToTile(canvas, clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = WIDTH / rect.width;
  const scaleY = HEIGHT / rect.height;
  const x = (clientX - rect.left) * scaleX;
  const y = (clientY - rect.top) * scaleY;

  return {
    col: Math.floor(x / TILE),
    row: Math.floor(y / TILE),
  };
}

function drawTile(context, col, row, tileType) {
  const x = col * TILE;
  const y = row * TILE;

  if (tileType === 1) {
    context.fillStyle = COLORS.wallShadow;
    context.fillRect(x, y, TILE, TILE);
    context.fillStyle = COLORS.wall;
    context.fillRect(x + 2, y + 10, TILE - 2, TILE - 10);
    context.fillStyle = COLORS.wallTop;
    context.fillRect(x + 2, y + 2, TILE - 2, 10);
    return;
  }

  if (tileType === 3) {
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

function drawStation(context, station, done) {
  const x = station.col * TILE;
  const y = station.row * TILE;

  context.fillStyle = station.color;
  context.fillRect(x + 12, y + 12, TILE - 24, TILE - 24);

  context.strokeStyle = done ? '#1d8a4f' : '#1f2937';
  context.lineWidth = 3;
  context.strokeRect(x + 12, y + 12, TILE - 24, TILE - 24);

  if (done) {
    context.fillStyle = '#1d8a4f';
    context.font = 'bold 14px Segoe UI';
    context.fillText('OK', x + 14, y + 43);
  }
}

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