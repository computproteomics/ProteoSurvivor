import { STATION_IDS, getStationTitle } from '../assets/stationConfig';
// Idle
import upIdle from '../assets/avatar_sprites/up_idle.png';
import rightIdle from '../assets/avatar_sprites/right_idle.png';
import downIdle from '../assets/avatar_sprites/down_idle.png';
import leftIdle from '../assets/avatar_sprites/left_idle.png';

// Walk
import up1 from '../assets/avatar_sprites/up_1.png';
import up2 from '../assets/avatar_sprites/up_2.png';

import right1 from '../assets/avatar_sprites/right_1.png';
import right2 from '../assets/avatar_sprites/right_2.png';

import down1 from '../assets/avatar_sprites/down_1.png';
import down2 from '../assets/avatar_sprites/down_2.png';

import left1 from '../assets/avatar_sprites/left_1.png';
import left2 from '../assets/avatar_sprites/left_2.png';

// ===============================
// Map Configuration
// ===============================
export const TILE = 48;
export const COLS = 22;
export const ROWS = 16;
export const WIDTH = COLS * TILE;
export const HEIGHT = ROWS * TILE;

// Player start position
export const PLAYER_START = { col: 2, row: 2 };

// ===============================
// Animation Configuration
// ===============================

// Total steps in our custom animation loop:
// [ step1, idle, step2, idle ]
export const WALK_FRAME_COUNT = 4;

// Time (ms) between frame changes
export const WALK_FRAME_DURATION = 120;

// ===============================
// Colors
// ===============================
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

// ===============================
// Sprite Storage
// ===============================
const walkSprites = [];
const idleSprites = [];

const directions = ['up', 'right', 'down', 'left'];

// ===============================
// Load Sprites (CALL ONCE ONLY)
// ===============================

export function loadSprites() {
  // Idle sprites
  idleSprites[0] = new Image();
  idleSprites[0].src = upIdle;

  idleSprites[1] = new Image();
  idleSprites[1].src = rightIdle;

  idleSprites[2] = new Image();
  idleSprites[2].src = downIdle;

  idleSprites[3] = new Image();
  idleSprites[3].src = leftIdle;

  // Walk sprites
  walkSprites[0] = [new Image(), new Image()];
  walkSprites[0][0].src = up1;
  walkSprites[0][1].src = up2;

  walkSprites[1] = [new Image(), new Image()];
  walkSprites[1][0].src = right1;
  walkSprites[1][1].src = right2;

  walkSprites[2] = [new Image(), new Image()];
  walkSprites[2][0].src = down1;
  walkSprites[2][1].src = down2;

  walkSprites[3] = [new Image(), new Image()];
  walkSprites[3][0].src = left1;
  walkSprites[3][1].src = left2;
}

// ===============================
// Animation State Update
// ===============================

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

// Station definitions with position on map and color
export const STATIONS = STATION_IDS.map((id) => ({
  id,
  label: getStationTitle(id),
  ...STATION_POSITIONS_BY_ID[id],
  color: STATION_COLORS[id],
}));

// Uses Manhattan distance so a station is reachable from adjacent tiles.
export function getNearbyStation(playerCol, playerRow) {
  return STATIONS.find((station) => {
    const distance = Math.abs(station.col - playerCol) + Math.abs(station.row - playerRow);
    return distance <= 1;
  });
}

// This function updates animation timing.
// It should be called every frame from your game loop.
export function updateAnimation(animState, now) {
  // If player is NOT moving → always show idle
  if (!animState.isMoving) {
    return {
      ...animState,
      frameIndex: 0,
      lastUpdate: now,
    };
  }

  // If enough time passed → advance frame
  if (now - animState.lastUpdate > WALK_FRAME_DURATION) {
    return {
      ...animState,
      frameIndex: (animState.frameIndex + 1) % WALK_FRAME_COUNT,
      lastUpdate: now,
    };
  }

  return animState;
}

// ===============================
// Map Layout (unchanged)
// ===============================
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
export function fitCanvasToViewport(canvas) {
  const scale = Math.min((window.innerWidth * 0.9) / WIDTH, (window.innerHeight * 0.75) / HEIGHT);
  canvas.style.width = `${Math.floor(WIDTH * scale)}px`;
  canvas.style.height = `${Math.floor(HEIGHT * scale)}px`;
}


// Finds a station exactly on one tile, used for direct click-to-enter.
export function getStationAtTile(col, row) {
  return STATIONS.find((station) => station.col === col && station.row === row);
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
// ===============================
// Movement config
// ===============================
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

// Finds a station exactly on one tile, used for direct click-to-enter.
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

// Draws a station marker and completion badge if it has been cleared.
function drawStation(context, station, done) {
  const x = station.col * TILE;
  const y = station.row * TILE;

  context.fillStyle = station.color;
  context.fillRect(x + 10, y + 10, TILE - 20, TILE - 20);

  context.strokeStyle = done ? '#1d8a4f' : '#1f2937';
  context.lineWidth = done ? 5 : 3;
  context.strokeRect(x + 10, y + 10, TILE - 20, TILE - 20);

  if (done) {
    const badgeX = x + TILE / 2;
    const badgeY = y + TILE / 2;

    context.save();
    context.fillStyle = '#16a34a';
    context.strokeStyle = '#ffffff';
    context.lineWidth = 2;
    context.beginPath();
    context.arc(badgeX, badgeY, 10, 0, Math.PI * 2);
    context.fill();
    context.stroke();

    context.fillStyle = '#ffffff';
    context.font = 'bold 12px Segoe UI';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText('✓', badgeX, badgeY + 0.5);
    context.restore();
  }
}

export const KEY_TO_DIRECTION = {
  arrowup: 'up',
  w: 'up',
  arrowdown: 'down',
  s: 'down',
  arrowleft: 'left',
  a: 'left',
  arrowright: 'right',
  d: 'right',
};

// ===============================
// Movement helpers
// ===============================
export function canMove(col, row) {
  if (row < 0 || row >= ROWS || col < 0 || col >= COLS) return false;
  const tile = MAP[row][col];
  return tile !== 1 && tile !== 3;
}

// ===============================
// DRAW PLAYER (ANIMATION CORE)
// ===============================
function drawPlayer(context, player, animState) {
  const { isMoving, direction, frameIndex } = animState;

  const cx = player.col * TILE;
  const cy = player.row * TILE;

  let img;

  // ===============================
  // ANIMATION LOGIC
  // ===============================

  if (!isMoving) {
    // If not moving → always use idle sprite
    img = idleSprites[direction];
  } else {
    // Custom animation cycle:
    // frameIndex cycles 0 → 1 → 2 → 3
    //
    // We map it like this:
    // 0 → step 1
    // 1 → idle
    // 2 → step 2
    // 3 → idle
    //
    // This creates a "bounce" walking effect

    switch (frameIndex) {
      case 0:
        img = walkSprites[direction][0]; // step 1
        break;
      case 1:
        img = idleSprites[direction]; // idle
        break;
      case 2:
        img = walkSprites[direction][1]; // step 2
        break;
      case 3:
        img = idleSprites[direction]; // idle
        break;
      default:
        img = idleSprites[direction];
    }
  }
  if (!img || !img.complete || img.naturalWidth === 0) return;

  context.drawImage(img, cx, cy, TILE, TILE);
}

// ===============================
// WORLD RENDER
// ===============================
export function renderWorld(context, player, completedSet, animState) {
  context.clearRect(0, 0, WIDTH, HEIGHT);

  // Draw tiles
  for (let row = 0; row < ROWS; row++) {
    for (let col = 0; col < COLS; col++) {
      drawTile(context, col, row, MAP[row][col]);
    }
  }

  // Draw stations (unchanged)
  STATIONS.forEach((station) =>
    drawStation(context, station, completedSet.has(station.id))
  );

  // Draw animated player
  drawPlayer(context, player, animState);
}
