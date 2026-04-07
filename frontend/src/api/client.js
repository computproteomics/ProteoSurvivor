import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
});

export const getLevels = () => api.get('/levels/');
export const getLevelDataset = (levelId) => api.get(`/levels/${levelId}/dataset/`);
export const createSession = (levelId) => api.post('/sessions/', { level_id: levelId });
export const submitAnswer = (sessionId, answer, timeTakenSeconds) =>
  api.post(`/sessions/${sessionId}/submit/`, { answer, time_taken_seconds: timeTakenSeconds });
export const getLeaderboard = () => api.get('/leaderboard/');

export default api;
