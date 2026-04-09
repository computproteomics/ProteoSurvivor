import axios from 'axios';

// Shared HTTP client for the frontend.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Station entry.
export const enterStation = (stationId, sessionId) =>
  api.post(`/stations/${stationId}/enter/`, { session_id: sessionId });

// Run station with given parameters.
export const runStation = (stationId, params) =>
  api.post(`/stations/${stationId}/run/`, { params });

export default api;
