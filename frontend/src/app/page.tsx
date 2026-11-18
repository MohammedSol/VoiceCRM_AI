"use client";

import { useEffect, useState } from "react";

interface HealthData {
  status: string;
  version: string;
}

export default function HomePage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const backendUrl =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  useEffect(() => {
    fetch(`${backendUrl}/health`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error ${res.status}`);
        }
        return res.json();
      })
      .then((data: HealthData) => {
        setHealth(data);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, [backendUrl]);

  return (
    <main
      style={{
        fontFamily: "system-ui, -apple-system, sans-serif",
        maxWidth: "600px",
        margin: "80px auto",
        padding: "0 20px",
      }}
    >
      <h1>Opportunity Voice Assistant</h1>
      <p>Sprint 0 — Page de statut</p>

      <section
        style={{
          marginTop: "32px",
          padding: "24px",
          border: "1px solid #e0e0e0",
          borderRadius: "8px",
          backgroundColor: loading
            ? "#f9fafb"
            : health
            ? "#f0fdf4"
            : "#fef2f2",
        }}
      >
        <h2 style={{ marginTop: 0 }}>Statut Backend</h2>
        {loading && <p>Vérification de l&apos;état du backend ({backendUrl})...</p>}
        {!loading && health && (
          <div>
            <p>
              Statut :{" "}
              <strong style={{ color: "#16a34a" }}>{health.status}</strong>
            </p>
            <p>
              Version : <code>{health.version}</code>
            </p>
            <p style={{ fontSize: "0.875rem", color: "#6b7280" }}>
              Backend joint avec succès sur {backendUrl}/health
            </p>
          </div>
        )}
        {!loading && error && (
          <div>
            <p style={{ color: "#dc2626" }}>
              Backend inaccessible sur <code>{backendUrl}/health</code>
            </p>
            <p style={{ fontSize: "0.875rem", color: "#6b7280" }}>
              Erreur : {error}
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
