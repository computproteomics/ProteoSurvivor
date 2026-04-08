import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { PLAYER_START } from '../screens/MapSetup';

const useGameStore = create(
  persist(
    (set, get) => ({
      // Player profile
      userId: null,
      userName: '',

      // Proteomics lab state
      completedStations: [],
      sessionId: null,
      stationParams: {},
      stationResults: null,
      mapPlayerPosition: PLAYER_START,

      // Generic data-analysis game state (kept for future levels)
      levels: [],
      leaderboard: [],
      currentLevel: null,
      currentSession: null,
      dataset: null,
      selectedAnswer: null,
      score: null,
      isLoading: false,
      error: null,
      startTime: null,

      // Proteomics actions
      setPlayerProfile: ({ userId, userName }) => set({ userId, userName }),
      setSessionId: (id) => set({ sessionId: id }),
      startLabSession: (id) =>
        set({
          sessionId: id,
          completedStations: [],
          stationParams: {},
          stationResults: null,
          mapPlayerPosition: PLAYER_START,
          score: null,
          error: null,
          startTime: Date.now(),
        }),
      markStationComplete: (stationId) =>
        set((state) => ({
          completedStations: [...new Set([...state.completedStations, stationId])],
        })),
      setStationParams: (stationId, params) =>
        set((state) => ({
          stationParams: { ...state.stationParams, [stationId]: params },
        })),
      setStationResults: (results) => set({ stationResults: results }),
      setMapPlayerPosition: (nextPosition) =>
        set((state) => ({
          mapPlayerPosition:
            typeof nextPosition === 'function'
              ? nextPosition(state.mapPlayerPosition)
              : nextPosition,
        })),

      // Generic actions
      setLevels: (levels) => set({ levels }),
      setLeaderboard: (leaderboard) => set({ leaderboard }),
      setCurrentLevel: (level) => set({ currentLevel: level }),
      setCurrentSession: (session) => set({ currentSession: session }),
      setDataset: (dataset) => set({ dataset }),
      setSelectedAnswer: (answer) => set({ selectedAnswer: answer }),
      setScore: (score) => set({ score }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),

      startTimer: () => set({ startTime: Date.now() }),
      getElapsedSeconds: () => {
        const { startTime } = get();
        return startTime ? Math.floor((Date.now() - startTime) / 1000) : 0;
      },

      reset: () =>
        set((state) => ({
          userId: state.userId,
          userName: state.userName,
          completedStations: [],
          sessionId: null,
          stationParams: {},
          stationResults: null,
          mapPlayerPosition: PLAYER_START,
          currentLevel: null,
          currentSession: null,
          dataset: null,
          selectedAnswer: null,
          score: null,
          error: null,
          startTime: null,
        })),
    }),
    {
      name: 'proteosurviver-game-state',
    }
  )
);

export default useGameStore;
