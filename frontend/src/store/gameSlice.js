import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { PLAYER_START } from '../screens/MapSetup';

// Base state used when the app first loads.
const INITIAL_STATE = {
  userId: null,
  userName: '',
  completedStations: [],
  sessionId: null,
  stationParams: {},
  stationResults: null,
  mapPlayerPosition: PLAYER_START,
};

// Session-only fields are reset when a new run starts.
const SESSION_STATE = {
  completedStations: [],
  sessionId: null,
  stationParams: {},
  stationResults: null,
  mapPlayerPosition: PLAYER_START,
};

const useGameStore = create(
  persist(
    (set) => ({
      ...INITIAL_STATE,
      // Keep the player identity, but update it when the intro form changes.
      setPlayerProfile: ({ userId, userName }) => set({ userId, userName }),
      // Start a fresh lab session without clearing the saved profile.
      startLabSession: (id) =>
        set({
          ...SESSION_STATE,
          sessionId: id,
        }),
      // Mark a station once its results have been completed.
      markStationComplete: (stationId) =>
        set((state) => ({
          completedStations: [...new Set([...state.completedStations, stationId])],
        })),
      // Store the latest parameters for the active station.
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
    }),
    {
      name: 'proteosurviver-game-state',
    }
  )
);

export default useGameStore;
