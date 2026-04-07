export default function WorldMap({ onSelectStation }) {
  return (
    <div>
      <h1>World Map</h1>

      <button onClick={() => onSelectStation("sample_prep")}>
        Sample Prep
      </button>

      <button onClick={() => onSelectStation("mass_spec")}>
        Mass Spec
      </button>

      <button onClick={() => onSelectStation("search_setup")}>
        Search Setup
      </button>

      <button onClick={() => onSelectStation("data_analysis")}>
        Data Analysis
      </button>

      <button onClick={() => onSelectStation("veit")}>
        Veit
      </button>
    </div>
  );
}