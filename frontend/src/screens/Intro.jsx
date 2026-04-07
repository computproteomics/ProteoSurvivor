export default function Intro({ onStart }) {
  return (
    <div>
      <h1>Welcome to Proteomics Game</h1>
      <button onClick={onStart}>Start</button>
    </div>
  );
}