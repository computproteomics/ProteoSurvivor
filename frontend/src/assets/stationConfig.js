import stationData from './stations.json';

const BACKGROUND_IMAGES = import.meta.glob('./backgrounds/*.{png,jpg,jpeg,webp}', {
  eager: true,
  import: 'default',
});

const BACKGROUND_BY_BASENAME = Object.fromEntries(
  Object.entries(BACKGROUND_IMAGES).map(([path, imageUrl]) => {
    const fileName = path.split('/').pop() ?? '';
    const baseName = fileName.replace(/\.[^.]+$/, '').toLowerCase();
    return [baseName, imageUrl];
  })
);

// Default config to use if a station config is missing or invalid.
const DEFAULT_STATION_CONFIG = {
  title: 'Station',
  description: 'No station information was found.',
  parameters: [],
};

export const STATION_BY_ID = stationData ?? {};
export const STATION_IDS = Object.keys(STATION_BY_ID);

export function getStationConfig(stationId) {
  return STATION_BY_ID[stationId] ?? DEFAULT_STATION_CONFIG;
}

export function getStationTitle(stationId) {
  return getStationConfig(stationId).title ?? DEFAULT_STATION_CONFIG.title;
}

export function getStationDescription(stationId) {
  return getStationConfig(stationId).description ?? DEFAULT_STATION_CONFIG.description;
}

export function getStationParameters(stationId) {
  return getStationConfig(stationId).parameters ?? DEFAULT_STATION_CONFIG.parameters;
}

export function getStationBackgroundImage(stationId) {
  if (!stationId) {
    return null;
  }

  const normalizedId = String(stationId).toLowerCase();

  return (
    BACKGROUND_BY_BASENAME[normalizedId] ??
    BACKGROUND_BY_BASENAME[normalizedId.replace(/^the_/, '')] ??
    null
  );
}