import axios from 'axios';

function readCookie(name) {
  const escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = document.cookie.match(new RegExp(`(?:^|; )${escapedName}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

// Shared HTTP client for the frontend.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || (import.meta.env.BASE_URL + 'api'),
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const csrfToken = readCookie('csrftoken');
  if (csrfToken) {
    config.headers['X-CSRFTOKEN'] = csrfToken;
  }
  return config;
});

// Start a new game: create or authenticate a user on backend.
export const startGame = ({ userName }) =>
  api.post('/start', {
    user_name: userName,
  });

// Station entry.
export const enterStation = (stationId, sessionId) =>
  api.post(`/stations/${stationId}/enter/`, { session_id: sessionId });

// Run station with given parameters.
export const runStation = (stationId, params) =>
  api.post(`/stations/${stationId}/run/`, { params });

export const getStationDataset = (stationId) =>
  api.get(`/stations/${stationId}/dataset/`);

export const getLeaderboard = () => api.get('/leaderboard/');

export const getScatterPlot = () => api.get('/scatter/');

export default api;
