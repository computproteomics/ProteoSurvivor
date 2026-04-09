import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Intro from './screens/Intro';
import WorldMap from './screens/WorldMap';
import StationView from './screens/StationView';
import ParametrizationView from './screens/ParametrizationView';
import StationResults from './screens/StationResults';
import Leaderboard from './screens/Leaderboard';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Intro />} />
        <Route path="/world" element={<WorldMap />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/station/:stationId" element={<StationView />} />
        <Route path="/station/:stationId/params" element={<ParametrizationView />} />
        <Route path="/station/:stationId/results" element={<StationResults />} />
      </Routes>
    </BrowserRouter>
  );
}
