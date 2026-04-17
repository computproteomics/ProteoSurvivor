import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Intro from './screens/Intro';
import BreakingNews from './screens/BreakingNews'
import WorldMap from './screens/WorldMap';
import StationView from './screens/StationView';
import ParametrizationView from './screens/ParametrizationView';
import StationResults from './screens/StationResults';
import Leaderboard from './screens/Leaderboard';
import useGameStore from './store/gameSlice';

function RequireAuth({ children }) {
  const userId = useGameStore((s) => s.userId);
  if (!userId) {
    return <Navigate to="/" replace />;
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Intro />} />
        <Route path="/news" element={<RequireAuth><BreakingNews /></RequireAuth>} />
        <Route path="/world" element={<RequireAuth><WorldMap /></RequireAuth>} />
        <Route path="/leaderboard" element={<RequireAuth><Leaderboard /></RequireAuth>} />
        <Route path="/station/:stationId" element={<RequireAuth><StationView /></RequireAuth>} />
        <Route path="/station/:stationId/params" element={<RequireAuth><ParametrizationView /></RequireAuth>} />
        <Route path="/station/:stationId/results" element={<RequireAuth><StationResults /></RequireAuth>} />
      </Routes>
    </BrowserRouter>
  );
}
