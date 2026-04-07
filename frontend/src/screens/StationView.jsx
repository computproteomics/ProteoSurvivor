import { useEffect, useState } from "react";

const stationContent = {
  sample_prep: {
    title: "Sample Preparation",
    description:
      "Prepare the infected and control samples for mass spectrometry. Open cells, isolate proteins, reduce disulfide bonds, alkylate, and digest with trypsin.",
    objective: "Complete the preparation workflow before moving to the mass spectrometer.",
  },
  mass_spec: {
    title: "Mass Spectrometer",
    description:
      "Run the samples on the mass spectrometer and choose an acquisition method.",
    objective: "Choose between DDA and DIA and start the acquisition.",
  },
  search_setup: {
    title: "Search Engine Setup",
    description:
      "Configure the search engine settings for your acquired data.",
    objective:
      "Choose enzyme, missed cleavages, and peptide length range before processing.",
  },
  data_analysis: {
    title: "Data Analysis",
    description:
      "Inspect results, identify regulated proteins, and determine which pathways are affected.",
    objective: "Interpret the data and prepare conclusions for Veit.",
  },
  veit: {
    title: "Veit",
    description:
      "Veit can guide you based on your progress and receive your final report.",
    objective: "Hand in your report when you are ready.",
  },
};

export default function StationView({
  stationId,
  sessionId,
  onBack,
  onComplete,
}) {
  const [stationData, setStationData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fallback = {
    title: "Unknown Station",
    description: "No station information was found.",
    objective: "Return to the map.",
  };

  const content = stationContent[stationId] || fallback;

  useEffect(() => {
    async function enterStation() {
      if (!stationId || !sessionId) return;

      setLoading(true);
      setError("");

      try {
        // Uncomment when backend is ready
        /*
        const response = await fetch(
          `http://127.0.0.1:8000/api/stations/${stationId}/enter/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ session_id: sessionId }),
          }
        );

        if (!response.ok) {
          throw new Error("Could not enter station.");
        }

        const data = await response.json();
        setStationData(data);
        */

        // Temporary fake backend response
        await new Promise((resolve) => setTimeout(resolve, 400));
        setStationData({
          message: `Entered station '${stationId}' successfully.`,
          station_id: stationId,
        });
      } catch (err) {
        setError(err.message || "Something went wrong while entering station.");
      } finally {
        setLoading(false);
      }
    }

    enterStation();
  }, [stationId, sessionId]);

  async function handleCompleteStation() {
    if (!stationId || !sessionId) return;

    setLoading(true);
    setError("");

    try {
      // Uncomment when backend is ready
      /*
      const response = await fetch(
        `http://127.0.0.1:8000/api/stations/${stationId}/complete/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ session_id: sessionId }),
        }
      );

      if (!response.ok) {
        throw new Error("Could not complete station.");
      }

      const data = await response.json();
      */

      // Temporary fake completion
      await new Promise((resolve) => setTimeout(resolve, 500));

      if (onComplete) {
        onComplete(stationId);
      }
    } catch (err) {
      setError(err.message || "Something went wrong while completing station.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>{content.title}</h1>
        <p style={styles.text}>{content.description}</p>

        <div style={styles.box}>
          <strong>Objective:</strong>
          <p style={{ marginTop: "0.5rem" }}>{content.objective}</p>
        </div>

        {loading && <p style={styles.info}>Loading station...</p>}
        {error && <p style={styles.error}>{error}</p>}

        {stationData && !loading && (
          <div style={styles.box}>
            <strong>Status:</strong>
            <p style={{ marginTop: "0.5rem" }}>{stationData.message}</p>
          </div>
        )}

        <div style={styles.buttonRow}>
          <button onClick={onBack} style={styles.secondaryButton}>
            Back to map
          </button>

          <button onClick={handleCompleteStation} style={styles.primaryButton}>
            Complete station
          </button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "#f4f6f8",
    padding: "2rem",
    display: "grid",
    placeItems: "center",
    fontFamily: "Arial, sans-serif",
  },
  card: {
    width: "min(800px, 92vw)",
    background: "white",
    borderRadius: "16px",
    padding: "2rem",
    boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
  },
  title: {
    marginTop: 0,
    marginBottom: "1rem",
  },
  text: {
    fontSize: "1rem",
    lineHeight: 1.6,
  },
  box: {
    marginTop: "1.25rem",
    padding: "1rem",
    background: "#f1f5f9",
    borderRadius: "10px",
  },
  info: {
    marginTop: "1rem",
    color: "#334155",
  },
  error: {
    marginTop: "1rem",
    color: "#b91c1c",
    fontWeight: "bold",
  },
  buttonRow: {
    display: "flex",
    gap: "1rem",
    marginTop: "1.5rem",
  },
  primaryButton: {
    padding: "0.75rem 1rem",
    border: "none",
    borderRadius: "10px",
    background: "#0f172a",
    color: "white",
    cursor: "pointer",
  },
  secondaryButton: {
    padding: "0.75rem 1rem",
    borderRadius: "10px",
    border: "1px solid #cbd5e1",
    background: "white",
    cursor: "pointer",
  },
};