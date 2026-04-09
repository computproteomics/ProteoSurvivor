import { STATION_IDS, getStationTitle } from '../assets/stationConfig';

=======
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
  // Idle sprites (one per direction)
  directions.forEach((dir, i) => {
    const img = new Image();
    img.src = `../assets/avatar_sprites/${dir}_idle.png`;
    idleSprites[i] = img;
  });

  // Walk sprites (we only use frame 1 and 2)
  directions.forEach((dir, dirIndex) => {
    walkSprites[dirIndex] = [];

    for (let frame = 0; frame < 2; frame++) {
      const img = new Image();
      img.src = `../assets/avatar_sprites/${dir}_${frame + 1}.png`;
      walkSprites[dirIndex][frame] = img;
    }
  });
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
=======
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
export const MAP = [/* same as yours */];

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
