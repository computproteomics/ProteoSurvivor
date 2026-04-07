import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Intro from './screens/Intro';
import WorldMap from './screens/WorldMap';
import StationView from './screens/StationView';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Intro />} />
        <Route path="/world" element={<WorldMap />} />
        <Route path="/station/:stationId" element={<StationView />} />
      </Routes>
    </BrowserRouter>
  );
}
