import stationData from './stations.json';

// Default config to use if a station config is missing or invalid.
const DEFAULT_STATION_CONFIG = {
  title: 'Station',
  description: 'No station information was found.',
  parameters: [],
};

export const STATION_BY_ID = stationData?.stations ?? {};
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