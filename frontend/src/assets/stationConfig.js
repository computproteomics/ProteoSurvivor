import stationData from './stations.json';

export const STATION_BY_ID = stationData.stations;
export const STATION_IDS = Object.keys(STATION_BY_ID);

export function getStationConfig(stationId) {
  return STATION_BY_ID[stationId];
}

export function getStationTitle(stationId) {
  return getStationConfig(stationId).title;
}

export function getStationDescription(stationId) {
  return getStationConfig(stationId).description;
}

export function getStationParameters(stationId) {
  return getStationConfig(stationId).parameters;
}