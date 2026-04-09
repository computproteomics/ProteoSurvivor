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

// ── Station icon drawers ─────────────────────────────────────────────────────
// Each function draws a vector icon centred at (cx, cy).
// Coordinates are relative to the translated origin and fill roughly ±20 px,
// matching the full 44×44 tile background (TILE − 4px margin on each side).
// The colour constant `dark` is used for strokes so icons read on any tile hue.
const SIGNIFICANCE_COLOR = '#c0392b'; // red threshold / significant dots
const BADGE_GREEN = '#1d8a4f';        // completion badge background
const BADGE_CHECK = '#ffffff';        // completion badge checkmark

// sample_prep: tilted test tube with liquid fill, cap and graduation marks
function drawIconSamplePrep(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(-Math.PI / 5);
  const dark = 'rgba(0,0,0,0.55)';
  ctx.strokeStyle = dark;
  ctx.lineWidth = 2;
  // Tube outline
  ctx.beginPath();
  ctx.moveTo(-6, -19);
  ctx.lineTo(-6, 10);
  ctx.arc(0, 10, 6, Math.PI, 0);
  ctx.lineTo(6, -19);
  ctx.stroke();
  // Cap
  ctx.fillStyle = 'rgba(0,0,0,0.15)';
  ctx.fillRect(-8, -22, 16, 5);
  ctx.strokeRect(-8, -22, 16, 5);
  // Liquid fill (lower 55%, clipped to tube interior)
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(-5.5, 1);
  ctx.lineTo(-5.5, 10);
  ctx.arc(0, 10, 5.5, Math.PI, 0);
  ctx.lineTo(5.5, 1);
  ctx.closePath();
  ctx.clip();
  ctx.fillStyle = 'rgba(255,255,255,0.55)';
  ctx.fillRect(-7, 1, 14, 16);
  ctx.restore();
  // Liquid surface line
  ctx.lineWidth = 1;
  ctx.strokeStyle = 'rgba(255,255,255,0.9)';
  ctx.beginPath();
  ctx.moveTo(-5.5, 1);
  ctx.lineTo(5.5, 1);
  ctx.stroke();
  // Graduation marks on right side of tube
  ctx.strokeStyle = dark;
  for (let i = 0; i < 5; i += 1) {
    ctx.beginPath();
    ctx.moveTo(6, -14 + i * 5);
    ctx.lineTo(9, -14 + i * 5);
    ctx.stroke();
  }
  // Glass highlight on left edge
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = 'rgba(255,255,255,0.5)';
  ctx.beginPath();
  ctx.moveTo(-4.5, -18);
  ctx.lineTo(-4.5, -5);
  ctx.stroke();
  ctx.restore();
}

// mass_spec: instrument body with inlet funnel, screen and signal readout
function drawIconMassSpec(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  const dark = 'rgba(0,0,0,0.55)';
  // Instrument body
  ctx.fillStyle = 'rgba(0,0,0,0.12)';
  ctx.fillRect(-17, -12, 24, 24);
  ctx.lineWidth = 2;
  ctx.strokeStyle = dark;
  ctx.strokeRect(-17, -12, 24, 24);
  // Internal screen
  ctx.fillStyle = 'rgba(0,0,0,0.22)';
  ctx.fillRect(-14, -9, 16, 12);
  // Screen scan lines
  ctx.lineWidth = 1;
  ctx.strokeStyle = 'rgba(255,255,255,0.35)';
  for (let i = 0; i < 3; i += 1) {
    ctx.beginPath();
    ctx.moveTo(-13, -7 + i * 4);
    ctx.lineTo(1, -7 + i * 4);
    ctx.stroke();
  }
  // Sample inlet funnel on left
  ctx.lineWidth = 1.8;
  ctx.strokeStyle = dark;
  ctx.beginPath();
  ctx.moveTo(-17, -5);
  ctx.lineTo(-21, -9);
  ctx.moveTo(-17, 5);
  ctx.lineTo(-21, 9);
  ctx.moveTo(-21, -9);
  ctx.lineTo(-21, 9);
  ctx.stroke();
  // Signal readout waveform on right
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.moveTo(7, 0);
  ctx.lineTo(9, 0);
  ctx.lineTo(10, -8);
  ctx.lineTo(11, 9);
  ctx.lineTo(12, -6);
  ctx.lineTo(13, 7);
  ctx.lineTo(14, -4);
  ctx.lineTo(15, 5);
  ctx.lineTo(16, 0);
  ctx.lineTo(20, 0);
  ctx.stroke();
  ctx.restore();
}

// spectral_search: magnifying glass with 6 spectral peaks inside the lens
function drawIconSpectralSearch(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  const dark = 'rgba(0,0,0,0.55)';
  // Lens circle
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = dark;
  ctx.beginPath();
  ctx.arc(-4, -4, 12, 0, Math.PI * 2);
  ctx.stroke();
  // Handle
  ctx.lineWidth = 4;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(6, 6);
  ctx.lineTo(18, 18);
  ctx.stroke();
  ctx.lineCap = 'butt';
  // Spectral peaks (baseline at y=4, peaks of varying heights)
  ctx.lineWidth = 1.5;
  const peakTops = [[-14, 4], [-11, -2], [-8, 3], [-5, -7], [-2, 0], [1, 2]];
  peakTops.forEach(([px, py]) => {
    ctx.beginPath();
    ctx.moveTo(px, 4);
    ctx.lineTo(px, py);
    ctx.stroke();
  });
  // Baseline inside lens
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(-15, 4);
  ctx.lineTo(3, 4);
  ctx.stroke();
  ctx.restore();
}

// filtering: funnel with 4 filter bars and a liquid drop at the spout
function drawIconFiltering(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  const dark = 'rgba(0,0,0,0.55)';
  // Funnel fill
  ctx.fillStyle = 'rgba(0,0,0,0.1)';
  ctx.beginPath();
  ctx.moveTo(-19, -18);
  ctx.lineTo(19, -18);
  ctx.lineTo(4, 2);
  ctx.lineTo(4, 16);
  ctx.lineTo(-4, 16);
  ctx.lineTo(-4, 2);
  ctx.closePath();
  ctx.fill();
  // Funnel outline
  ctx.lineWidth = 2;
  ctx.strokeStyle = dark;
  ctx.beginPath();
  ctx.moveTo(-19, -18);
  ctx.lineTo(19, -18);
  ctx.lineTo(4, 2);
  ctx.lineTo(4, 16);
  ctx.lineTo(-4, 16);
  ctx.lineTo(-4, 2);
  ctx.closePath();
  ctx.stroke();
  // Filter mesh lines (4 lines of decreasing span inside funnel)
  ctx.lineWidth = 1.5;
  for (let i = 0; i < 4; i += 1) {
    const t = i / 3;
    const lx = -19 + t * 15;
    const rx = 19 - t * 15;
    const fy = -18 + t * 20;
    ctx.beginPath();
    ctx.moveTo(lx + 2, fy);
    ctx.lineTo(rx - 2, fy);
    ctx.stroke();
  }
  // Liquid drop at spout end
  ctx.fillStyle = 'rgba(255,255,255,0.7)';
  ctx.strokeStyle = dark;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(0, 20, 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

// transform: 270° circular arrow, central molecule and three satellite atoms
function drawIconTransform(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  const dark = 'rgba(0,0,0,0.55)';
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = dark;
  // 270° arc from top, clockwise
  ctx.beginPath();
  ctx.arc(0, 0, 14, -Math.PI / 2, Math.PI, false);
  ctx.stroke();
  // Arrowhead at arc end (arc ends at (−14, 0), pointing downward)
  ctx.beginPath();
  ctx.moveTo(-14, 0);
  ctx.lineTo(-9, -5);
  ctx.moveTo(-14, 0);
  ctx.lineTo(-9, 5);
  ctx.stroke();
  // Central molecule
  ctx.fillStyle = dark;
  ctx.beginPath();
  ctx.arc(0, 0, 4, 0, Math.PI * 2);
  ctx.fill();
  // Bond lines to satellite atoms
  ctx.lineWidth = 1;
  [[9, 0], [-4, 8], [-4, -8]].forEach(([dx, dy]) => {
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(dx, dy);
    ctx.stroke();
  });
  // Satellite atoms
  ctx.fillStyle = 'rgba(0,0,0,0.35)';
  [[9, 0], [-4, 8], [-4, -8]].forEach(([dx, dy]) => {
    ctx.beginPath();
    ctx.arc(dx, dy, 2.5, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.restore();
}

// normalize: filled Gaussian bell curve, baseline, dashed mean and σ tick marks
function drawIconNormalize(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  const dark = 'rgba(0,0,0,0.55)';
  const baseline = 10;
  const peak = -16;
  // Filled area under bell curve
  ctx.fillStyle = 'rgba(0,0,0,0.12)';
  ctx.beginPath();
  ctx.moveTo(-20, baseline);
  ctx.bezierCurveTo(-14, baseline, -10, peak, 0, peak);
  ctx.bezierCurveTo(10, peak, 14, baseline, 20, baseline);
  ctx.closePath();
  ctx.fill();
  // Bell curve outline
  ctx.lineWidth = 2;
  ctx.strokeStyle = dark;
  ctx.beginPath();
  ctx.moveTo(-20, baseline);
  ctx.bezierCurveTo(-14, baseline, -10, peak, 0, peak);
  ctx.bezierCurveTo(10, peak, 14, baseline, 20, baseline);
  ctx.stroke();
  // Baseline axis
  ctx.beginPath();
  ctx.moveTo(-20, baseline);
  ctx.lineTo(20, baseline);
  ctx.stroke();
  // Dashed mean line
  ctx.lineWidth = 1.5;
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(0, peak);
  ctx.lineTo(0, baseline);
  ctx.stroke();
  ctx.setLineDash([]);
  // ±1σ tick marks on baseline
  ctx.lineWidth = 1.2;
  [-10, 10].forEach((sx) => {
    ctx.beginPath();
    ctx.moveTo(sx, baseline);
    ctx.lineTo(sx, baseline - 5);
    ctx.stroke();
  });
  ctx.restore();
}

// imputer: horizontal syringe with barrel, liquid fill, ticks, plunger, needle
function drawIconImputer(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  const dark = 'rgba(0,0,0,0.55)';
  // Barrel outline
  ctx.lineWidth = 2;
  ctx.strokeStyle = dark;
  ctx.strokeRect(-13, -7, 22, 14);
  // Liquid fill inside barrel
  ctx.fillStyle = 'rgba(255,255,255,0.55)';
  ctx.fillRect(-12, -6, 12, 12);
  // Liquid surface (vertical line)
  ctx.lineWidth = 1;
  ctx.strokeStyle = 'rgba(255,255,255,0.9)';
  ctx.beginPath();
  ctx.moveTo(-1, -6);
  ctx.lineTo(-1, 6);
  ctx.stroke();
  // Graduation ticks on barrel top
  ctx.strokeStyle = dark;
  for (let i = 0; i < 5; i += 1) {
    ctx.beginPath();
    ctx.moveTo(-10 + i * 4, -7);
    ctx.lineTo(-10 + i * 4, -4);
    ctx.stroke();
  }
  // Needle (right side, tapering to tip)
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(9, -2);
  ctx.lineTo(20, 0);
  ctx.lineTo(9, 2);
  ctx.stroke();
  // Plunger rod (left side)
  ctx.beginPath();
  ctx.moveTo(-13, 0);
  ctx.lineTo(-19, 0);
  ctx.stroke();
  // Plunger flanges
  ctx.beginPath();
  ctx.moveTo(-17, -4);
  ctx.lineTo(-17, 4);
  ctx.moveTo(-19, -4);
  ctx.lineTo(-19, 4);
  ctx.stroke();
  ctx.restore();
}

// multiple_testing_corrector: filled bar chart with p-value threshold line
function drawIconMTC(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  const dark = 'rgba(0,0,0,0.55)';
  const baseY = 11;
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = dark;
  // X axis
  ctx.beginPath();
  ctx.moveTo(-20, baseY);
  ctx.lineTo(20, baseY);
  ctx.stroke();
  // Each entry is [barX, barHeight] – 5 bars of descending height (sorted p-values)
  const bars = [[-18, 20], [-11, 14], [-4, 10], [3, 7], [10, 5]];
  bars.forEach(([bx, h]) => {
    ctx.fillStyle = 'rgba(0,0,0,0.15)';
    ctx.fillRect(bx, baseY - h, 5, h);
    ctx.strokeRect(bx, baseY - h, 5, h);
  });
  // Dashed significance threshold
  ctx.setLineDash([3, 3]);
  ctx.strokeStyle = SIGNIFICANCE_COLOR;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(-20, 4);
  ctx.lineTo(20, 4);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();
}

// the_cutter: scissors with pivot, blade arms, handle rings and cut line
function drawIconCutter(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  const dark = 'rgba(0,0,0,0.55)';
  ctx.strokeStyle = dark;
  ctx.lineWidth = 2;
  // Pivot circle
  ctx.beginPath();
  ctx.arc(0, 0, 3, 0, Math.PI * 2);
  ctx.stroke();
  // Upper blade arm (no tip circle)
  ctx.beginPath();
  ctx.moveTo(2, -2);
  ctx.lineTo(12, -10);
  ctx.stroke();
  // Lower blade arm (no tip circle)
  ctx.beginPath();
  ctx.moveTo(2, 2);
  ctx.lineTo(12, 10);
  ctx.stroke();
  // Upper handle arm and ring
  ctx.beginPath();
  ctx.moveTo(-2, -2);
  ctx.lineTo(-9, -7);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(-9, -7, 5, 0, Math.PI * 2);
  ctx.stroke();
  // Lower handle arm and ring
  ctx.beginPath();
  ctx.moveTo(-2, 2);
  ctx.lineTo(-9, 7);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(-9, 7, 5, 0, Math.PI * 2);
  ctx.stroke();
  // Dashed line being cut (extending to the right of the blades)
  ctx.setLineDash([3, 3]);
  ctx.lineWidth = 1;
  ctx.strokeStyle = 'rgba(0,0,0,0.35)';
  ctx.beginPath();
  ctx.moveTo(3, 0);
  ctx.lineTo(15, 0);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();
}

// statistical_analysis: volcano plot – axes, V-lines, p-value threshold, dots
function drawIconStatAnalysis(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  const dark = 'rgba(0,0,0,0.55)';
  const baseY = 14;
  // Axes
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = dark;
  ctx.beginPath();
  ctx.moveTo(-19, baseY);
  ctx.lineTo(19, baseY);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(0, baseY);
  ctx.lineTo(0, -18);
  ctx.stroke();
  // V-shaped fold-change cutoff lines
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(-19, baseY);
  ctx.lineTo(-8, -2);
  ctx.moveTo(19, baseY);
  ctx.lineTo(8, -2);
  ctx.stroke();
  // Dashed p-value threshold
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(-19, -2);
  ctx.lineTo(19, -2);
  ctx.stroke();
  ctx.setLineDash([]);
  // Dots above threshold (statistically significant)
  const significantDots = [[-14, -7], [-17, -13], [-12, -10], [15, -9], [12, -14], [17, -6]];
  significantDots.forEach(([dx, dy]) => {
    ctx.fillStyle = SIGNIFICANCE_COLOR;
    ctx.beginPath();
    ctx.arc(dx, dy, 2, 0, Math.PI * 2);
    ctx.fill();
  });
  // Dots below / inside V-lines (non-significant)
  const nonSignificantDots = [[-3, 4], [2, 7], [-6, 2], [5, 5], [-1, 10], [7, 3], [-9, 6]];
  nonSignificantDots.forEach(([dx, dy]) => {
    ctx.fillStyle = 'rgba(0,0,0,0.25)';
    ctx.beginPath();
    ctx.arc(dx, dy, 1.5, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.restore();
}

// veit: stick-figure person with filled lab-coat body and lapels
function drawIconVeit(ctx, cx, cy) {
  ctx.save();
  ctx.translate(cx, cy);
  const dark = 'rgba(0,0,0,0.55)';
  ctx.strokeStyle = dark;
  ctx.lineWidth = 2;
  // Head
  ctx.beginPath();
  ctx.arc(0, -13, 6, 0, Math.PI * 2);
  ctx.stroke();
  // Lab coat body (filled white rectangle)
  ctx.fillStyle = 'rgba(255,255,255,0.55)';
  ctx.fillRect(-8, -6, 16, 14);
  ctx.strokeRect(-8, -6, 16, 14);
  // Lab coat lapels
  ctx.beginPath();
  ctx.moveTo(-8, -6);
  ctx.lineTo(0, 0);
  ctx.lineTo(8, -6);
  ctx.stroke();
  // Arms
  ctx.beginPath();
  ctx.moveTo(-8, -4);
  ctx.lineTo(-14, 4);
  ctx.moveTo(8, -4);
  ctx.lineTo(14, 4);
  ctx.stroke();
  // Legs
  ctx.beginPath();
  ctx.moveTo(-4, 8);
  ctx.lineTo(-6, 18);
  ctx.moveTo(4, 8);
  ctx.lineTo(6, 18);
  ctx.stroke();
  // Neck
  ctx.beginPath();
  ctx.moveTo(0, -7);
  ctx.lineTo(0, -6);
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

// Draws a station marker (full tile, no border) and completion badge if cleared.
function drawStation(context, station, done) {
  const x = station.col * TILE;
  const y = station.row * TILE;

  // Fill the full tile (2 px margin so it sits flush against neighbours).
  context.fillStyle = station.color;
  context.fillRect(x + 2, y + 2, TILE - 4, TILE - 4);

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
    context.fillStyle = BADGE_GREEN;
    context.beginPath();
    context.arc(x + TILE - 10, y + 10, 8, 0, Math.PI * 2);
    context.fill();
    context.strokeStyle = BADGE_CHECK;
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
