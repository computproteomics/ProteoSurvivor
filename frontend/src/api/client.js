import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Proteomics lab station endpoints
export const enterStation = (stationId, sessionId) =>
  api.post(`/stations/${stationId}/enter/`, { session_id: sessionId });
export const completeStation = (stationId, sessionId) =>
  api.post(`/stations/${stationId}/complete/`, { session_id: sessionId });
export const runStation = (stationId, params) =>
  api.post(`/stations/${stationId}/run/`, { params });

// Data analysis game endpoints
export const getLevels = () => api.get('/levels/');
export const getLevelDataset = (levelId) => api.get(`/levels/${levelId}/dataset/`);
export const createSession = (levelId) => api.post('/sessions/', { level_id: levelId });
export const submitAnswer = (sessionId, answer, timeTakenSeconds) =>
  api.post(`/sessions/${sessionId}/submit/`, { answer, time_taken_seconds: timeTakenSeconds });
export const getLeaderboard = () => api.get('/leaderboard/');

export default api;
