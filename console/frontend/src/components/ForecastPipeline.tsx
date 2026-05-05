// This project was developed with assistance from AI tools.

import { useEffect, useState } from "react";

interface ForecastPipelineProps {
  active: boolean;
  forecastPublished: boolean;
  riskCount: number;
  onClose: () => void;
}

const STEPS = [
  { label: "Earth2Studio", desc: "Retrieves global forecast as model input" },
  { label: "GEFS Input", desc: "25km global ensemble forecast" },
  { label: "CorrDiff NIM", desc: "Generates local 3km forecast from global data" },
  { label: "Risk Scoring", desc: "Evaluates exposure for each asset" },
  { label: "Assets Ranked", desc: "Prioritized for monitoring" },
];

export function ForecastPipeline({ active, forecastPublished, riskCount, onClose }: ForecastPipelineProps) {
  const [step4Done, setStep4Done] = useState(false);

  useEffect(() => {
    if (active) setStep4Done(false);
  }, [active]);

  useEffect(() => {
    if (riskCount <= 0) return;
    const t = setTimeout(() => setStep4Done(true), 1000);
    return () => clearTimeout(t);
  }, [riskCount]);

  if (!active) return null;

  const completed = [
    active,
    active,
    forecastPublished,
    riskCount > 0,
    step4Done,
  ];

  const activeStep = completed.filter(Boolean).length;

  return (
    <div style={{
      position: "absolute",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      zIndex: 999,
      whiteSpace: "nowrap" as const,
      background: "rgba(21,21,21,0.92)",
      borderRadius: 6,
      border: "1px solid rgba(255,255,255,0.1)",
      padding: "14px 16px 12px",
      color: "#fff",
      fontFamily: "Inter, sans-serif",
      backdropFilter: "blur(8px)",
      boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, color: "rgba(255,255,255,0.6)" }}>
          Earth-2 Forecast Pipeline
        </span>
        <button
          onClick={onClose}
          style={{ background: "none", border: "none", color: "rgba(255,255,255,0.4)", cursor: "pointer", fontSize: 16, lineHeight: 1, padding: 0 }}
        >
          ×
        </button>
      </div>

      {STEPS.map((step, i) => {
        const done = completed[i];
        const isCurrent = i === activeStep && !done;
        return (
          <div key={i} style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
            padding: "6px 0",
            opacity: done ? 1 : isCurrent ? 0.9 : 0.35,
          }}>
            <span style={{
              width: 18,
              height: 18,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 12,
              flexShrink: 0,
              marginTop: 1,
            }}>
              {done ? (
                <span style={{ color: "#3E8635" }}>✓</span>
              ) : isCurrent ? (
                <span style={{ animation: "grid-fault-pulse 1.2s ease-in-out infinite", color: "#F0AB00" }}>◉</span>
              ) : (
                <span style={{ color: "rgba(255,255,255,0.3)" }}>○</span>
              )}
            </span>
            <div style={{ flex: 1, fontSize: 13 }}>
              <span style={{ fontWeight: 600 }}>{step.label}:</span>{" "}
              <span style={{ fontWeight: 400, color: "rgba(255,255,255,0.75)" }}>{step.desc}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
