import React from "react";
import Link from "next/link";
import { Call } from "@/lib/api";
import { UrgencyBadge } from "@/components/UrgencyBadge";
import { Phone, Clock, ChevronRight, MessageSquare } from "lucide-react";

interface CallItemProps {
  call: Call;
}

export function CallItem({ call }: CallItemProps) {
  const formattedDate = call.created_at
    ? new Date(call.created_at).toLocaleString()
    : "Recent";

  return (
    <Link
      href={`/calls/${call.id}`}
      className="glass-card p-4 rounded-2xl flex items-center justify-between gap-4 block group"
    >
      <div className="flex items-center gap-4">
        <div className="h-12 w-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center shrink-0 group-hover:border-primary/50 group-hover:bg-primary/10 transition-all">
          <Phone className="h-5 w-5 text-slate-300 group-hover:text-primary transition-colors" />
        </div>

        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-semibold text-white text-base">
              {call.caller_name || call.caller_phone}
            </h4>
            {call.caller_name && (
              <span className="text-xs text-slate-400 font-mono">
                {call.caller_phone}
              </span>
            )}
            <UrgencyBadge score={call.urgency_score} riskLevel={call.risk_level} />
          </div>

          <div className="flex items-center gap-4 mt-1.5 text-xs text-slate-400 flex-wrap">
            <span className="capitalize px-2 py-0.5 rounded bg-white/5 font-medium text-slate-300">
              {call.intent}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {call.duration_seconds}s
            </span>
            <span className="uppercase text-[10px] font-mono font-semibold text-cyan-400">
              {call.language}
            </span>
            <span>{formattedDate}</span>
          </div>

          {call.summary && (
            <p className="text-xs text-slate-300 mt-2 line-clamp-1 italic text-slate-400 flex items-center gap-1.5">
              <MessageSquare className="h-3 w-3 shrink-0" />
              &ldquo;{call.summary}&rdquo;
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 text-slate-400 group-hover:text-white transition-colors">
        <span className="text-xs font-medium hidden sm:inline">Inspect</span>
        <ChevronRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
      </div>
    </Link>
  );
}
