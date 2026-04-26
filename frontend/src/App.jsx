import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Intro from './screens/Intro';
import BreakingNews from './screens/BreakingNews'
import WorldMap from './screens/WorldMap';
import StationView from './screens/StationView';
import ParametrizationView from './screens/ParametrizationView';
import StationResults from './screens/StationResults';
import Leaderboard from './screens/Leaderboard';
import Credits from './screens/Credits';
import useGameStore from './store/gameSlice';

function RequireAuth({ children }) {
  const userId = useGameStore((s) => s.userId);
  if (!userId) {
    return <Navigate to="/" replace />;
  }
  return children;
}

export default function App() {
  // import.meta.env.BASE_URL is set by Vite's `base` config option (default '/').
  // Strip the trailing slash so React Router's basename works correctly, e.g.
  // '/ProteoSurviver/' → '/ProteoSurviver', '/' → ''.
  const basename = import.meta.env.BASE_URL.replace(/\/$/, '');
  return (
    <BrowserRouter basename={basename}>
      <Routes>
        <Route path="/" element={<Intro />} />
        <Route path="/news" element={<RequireAuth><BreakingNews /></RequireAuth>} />
        <Route path="/world" element={<RequireAuth><WorldMap /></RequireAuth>} />
        <Route path="/leaderboard" element={<RequireAuth><Leaderboard /></RequireAuth>} />
        <Route path="/credits" element={<RequireAuth><Credits /></RequireAuth>} />
        <Route path="/station/:stationId" element={<RequireAuth><StationView /></RequireAuth>} />
        <Route path="/station/:stationId/params" element={<RequireAuth><ParametrizationView /></RequireAuth>} />
        <Route path="/station/:stationId/results" element={<RequireAuth><StationResults /></RequireAuth>} />
      </Routes>
    </BrowserRouter>
  );
}
