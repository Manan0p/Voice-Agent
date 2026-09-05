import React from "react";

interface UrgencyBadgeProps {
  score: number;
  riskLevel?: string;
}

export function UrgencyBadge({ score, riskLevel }: UrgencyBadgeProps) {
  let color = "bg-slate-800 text-slate-300 border-slate-700";
  let label = "Routine";

  if (score >= 0.75 || riskLevel === "critical" || riskLevel === "scam") {
    color = "bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse";
    label = "Critical";
  } else if (score >= 0.5) {
    color = "bg-amber-500/20 text-amber-300 border-amber-500/40";
    label = "High";
  } else if (score >= 0.25) {
    color = "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
    label = "Moderate";
  } else {
    color = "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
    label = "Low";
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${color}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label} ({score.toFixed(2)})
    </span>
  );
}
