import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Intro from './screens/Intro';
import BreakingNews from './screens/BreakingNews'
import AssignmentIntro from './screens/AssignmentIntro';
import WorldMap from './screens/WorldMap';
import StationView from './screens/StationView';
import ParametrizationView from './screens/ParametrizationView';
import StationResults from './screens/StationResults';
import Leaderboard from './screens/Leaderboard';
import Credits from './screens/Credits';
import useGameStore from './store/gameSlice';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled render error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '1.5rem' }}>
          <div
            style={{
              width: 'min(680px, 92vw)',
              background: '#ffffff',
              borderRadius: '14px',
              border: '1px solid #dbe2ea',
              boxShadow: '0 12px 30px rgba(16, 24, 40, 0.1)',
              padding: '1.5rem',
              color: '#1f2937',
              fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
            }}
          >
            <h1 style={{ marginTop: 0, marginBottom: '0.5rem' }}>Something went wrong</h1>
            <p style={{ marginTop: 0, marginBottom: '1rem', lineHeight: 1.5 }}>
              An unexpected UI error occurred. Please reload the page to continue.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              style={{
                border: '1px solid #334155',
                borderRadius: '10px',
                background: '#0f172a',
                color: '#ffffff',
                padding: '0.6rem 0.95rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Reload app
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

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
    <ErrorBoundary>
      <BrowserRouter basename={basename}>
        <Routes>
          <Route path="/" element={<Intro />} />
          <Route path="/news" element={<RequireAuth><BreakingNews /></RequireAuth>} />
          <Route path="/assignment" element={<RequireAuth><AssignmentIntro /></RequireAuth>} />
          <Route path="/world" element={<RequireAuth><WorldMap /></RequireAuth>} />
          <Route path="/leaderboard" element={<RequireAuth><Leaderboard /></RequireAuth>} />
          <Route path="/credits" element={<RequireAuth><Credits /></RequireAuth>} />
          <Route path="/station/:stationId" element={<RequireAuth><StationView /></RequireAuth>} />
          <Route path="/station/:stationId/params" element={<RequireAuth><ParametrizationView /></RequireAuth>} />
          <Route path="/station/:stationId/results" element={<RequireAuth><StationResults /></RequireAuth>} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
