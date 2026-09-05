"use client";

import React, { useState } from "react";
import { Phone, PhoneOff, UserCheck, ShieldAlert, Radio, Mic } from "lucide-react";
import { api } from "@/lib/api";

interface LiveCallProps {
  callId: string;
  callerPhone: string;
  callerName?: string;
  intent?: string;
  urgencyScore?: number;
  onActionComplete?: () => void;
}

export function LiveCallCard({
  callId,
  callerPhone,
  callerName = "Unknown Caller",
  intent = "Incoming Call",
  urgencyScore = 0.5,
  onActionComplete,
}: LiveCallProps) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleTakeCall = async () => {
    setLoadingAction("take");
    try {
      const res = await api.takeCall(callId, "PJSIP/1002", "User takeover from dashboard");
      setStatusMessage(res.message);
      onActionComplete?.();
    } catch (e: any) {
      alert(`Takeover failed: ${e.message}`);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleKeepAi = async () => {
    setLoadingAction("keep");
    try {
      const res = await api.keepAi(callId, "User approved AI handling");
      setStatusMessage(res.message);
      onActionComplete?.();
    } catch (e: any) {
      alert(`Keep AI failed: ${e.message}`);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleEndCall = async () => {
    if (!confirm("Are you sure you want to disconnect this live call?")) return;
    setLoadingAction("end");
    try {
      const res = await api.endCall(callId, "User force hangup from dashboard");
      setStatusMessage(res.message);
      onActionComplete?.();
    } catch (e: any) {
      alert(`End call failed: ${e.message}`);
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <div className="glass-panel-glow p-6 rounded-3xl border border-primary/40 relative overflow-hidden">
      {/* Background glowing gradient */}
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-primary/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-2xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center animate-pulse">
            <Radio className="h-5 w-5 text-rose-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-rose-400">
                LIVE CALL IN PROGRESS
              </span>
              <span className="h-2 w-2 rounded-full bg-rose-500 animate-ping" />
            </div>
            <h3 className="text-xl font-bold text-white mt-0.5">
              {callerName} <span className="text-sm font-normal text-slate-400">({callerPhone})</span>
            </h3>
          </div>
        </div>

        {/* Audio Waveform Animation */}
        <div className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-black/40 border border-white/10">
          <Mic className="h-4 w-4 text-cyan-400 mr-2 animate-bounce" />
          {[40, 80, 20, 90, 60, 100, 30, 70].map((h, i) => (
            <span
              key={i}
              style={{ height: `${Math.max(6, (h * 24) / 100)}px` }}
              className="w-1 bg-gradient-to-t from-primary to-accent-cyan rounded-full animate-waveform"
            />
          ))}
          <span className="text-xs text-slate-300 ml-2 font-mono">AI Conversing</span>
        </div>
      </div>

      {/* Summary / Intent Tag */}
      <div className="flex items-center gap-3 my-4">
        <span className="text-xs font-medium px-3 py-1 rounded-lg bg-surfaceLight border border-white/10 text-slate-300">
          Intent: <strong className="text-white capitalize">{intent}</strong>
        </span>
        <span className="text-xs font-medium px-3 py-1 rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-300 flex items-center gap-1.5">
          <ShieldAlert className="h-3.5 w-3.5" />
          Urgency Score: <strong>{urgencyScore.toFixed(2)}</strong>
        </span>
      </div>

      {statusMessage && (
        <div className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300">
          {statusMessage}
        </div>
      )}

      {/* Human Intervention Action Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-white/10">
        <button
          onClick={handleTakeCall}
          disabled={loadingAction !== null}
          className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm transition-all shadow-lg shadow-emerald-600/30 active:scale-95 disabled:opacity-50"
        >
          <Phone className="h-4 w-4" />
          {loadingAction === "take" ? "Bridging..." : "Take Call (Bridge)"}
        </button>

        <button
          onClick={handleKeepAi}
          disabled={loadingAction !== null}
          className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-surfaceLight hover:bg-white/10 text-slate-200 border border-white/10 font-semibold text-sm transition-all active:scale-95 disabled:opacity-50"
        >
          <UserCheck className="h-4 w-4 text-cyan-400" />
          {loadingAction === "keep" ? "Confirming..." : "Keep AI Handling"}
        </button>

        <button
          onClick={handleEndCall}
          disabled={loadingAction !== null}
          className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-500/30 font-semibold text-sm transition-all active:scale-95 disabled:opacity-50"
        >
          <PhoneOff className="h-4 w-4" />
          {loadingAction === "end" ? "Disconnecting..." : "End Call"}
        </button>
      </div>
    </div>
  );
}
