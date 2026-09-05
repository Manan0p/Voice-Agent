import React from "react";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  colorClass?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  colorClass = "text-primary",
}: StatCardProps) {
  return (
    <div className="glass-card p-5 rounded-2xl flex items-center justify-between">
      <div>
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          {title}
        </p>
        <p className="text-2xl font-bold text-white mt-1">{value}</p>
        {subtitle && (
          <p className="text-xs text-slate-400 mt-1 font-medium">{subtitle}</p>
        )}
      </div>
      <div
        className={`h-12 w-12 rounded-xl bg-white/5 flex items-center justify-center border border-white/10 ${colorClass}`}
      >
        <Icon className="h-6 w-6" />
      </div>
    </div>
  );
}
