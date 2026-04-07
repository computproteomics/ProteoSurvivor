import { useState } from "react";
import Intro from "./screens/Intro";
import WorldMap from "./screens/WorldMap";
import StationView from "./screens/StationView";

export default function App() {
  const [screen, setScreen] = useState("intro");
  const [selectedStation, setSelectedStation] = useState(null);

  // Fake session for now (replace later with backend)
  const sessionId = 1;

  function handleStart() {
    setScreen("world");
  }

  function handleEnterStation(stationId) {
    setSelectedStation(stationId);
    setScreen("station");
  }

  function handleBackToMap() {
    setScreen("world");
  }

  function handleCompleteStation(stationId) {
    console.log("Completed:", stationId);

    // Later: update progression / call backend
    setScreen("world");
  }

  // 🔹 Intro screen
  if (screen === "intro") {
    return <Intro onStart={handleStart} />;
  }

  // 🔹 World map
  if (screen === "world") {
    return <WorldMap onSelectStation={handleEnterStation} />;
  }

  // 🔹 Station view
  if (screen === "station") {
    return (
      <StationView
        stationId={selectedStation}
        sessionId={sessionId}
        onBack={handleBackToMap}
        onComplete={handleCompleteStation}
      />
    );
  }

  // 🔹 Result screen (you can build later)
  if (screen === "result") {
    return <h1>Results (coming soon)</h1>;
  }

  return null;
}