"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, CallDetail } from "@/lib/api";
import { TranscriptBubble } from "@/components/TranscriptBubble";
import { UrgencyBadge } from "@/components/UrgencyBadge";
import {
  ArrowLeft,
  Phone,
  Clock,
  Globe,
  Shield,
  FileText,
  PhoneCall,
  UserCheck,
  PhoneOff,
} from "lucide-react";

export default function CallDetailPage() {
  const params = useParams();
  const callId = params?.id as string;

  const [call, setCall] = useState<CallDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [handoffMsg, setHandoffMsg] = useState<string | null>(null);

  useEffect(() => {
    const fetchCall = async () => {
      try {
        setLoading(true);
        const data = await api.getCallById(callId);
        setCall(data);
      } catch (e) {
        console.error("Failed to load call detail:", e);
        // Fallback demo detail for immediate UI preview
        setCall({
          id: callId,
          caller_phone: "+91-98765-43210",
          caller_name: "Rahul Sharma",
          intent: "personal",
          urgency_score: 0.65,
          risk_level: "low",
          language: "hinglish",
          status: "completed",
          duration_seconds: 42,
          created_at: new Date().toISOString(),
          summary: "Caller Rahul asked if Manan was free for a project meeting on Wednesday. AI confirmed and recorded note.",
          messages: [
            {
              id: "m-1",
              speaker: "caller",
              content: "Hello, bhai Manan free hai kya kal meeting ke liye?",
              language: "hinglish",
              timestamp: new Date(Date.now() - 30000).toISOString(),
            },
            {
              id: "m-2",
              speaker: "agent",
              content: "Namaste! Manan abhi busy hain. Kya main koi message note kar loon?",
              language: "hinglish",
              timestamp: new Date(Date.now() - 20000).toISOString(),
            },
            {
              id: "m-3",
              speaker: "caller",
              content: "Haan bhai, unko bolna Wednesday 3 PM meeting shift kar sakte hain kya?",
              language: "hinglish",
              timestamp: new Date(Date.now() - 10000).toISOString(),
            },
            {
              id: "m-4",
              speaker: "agent",
              content: "Theek hai Rahul ji, maine note kar liya hai. Main Manan ko notify kar doonga.",
              language: "hinglish",
              timestamp: new Date().toISOString(),
            },
          ],
          audit_logs: [],
        });
      } finally {
        setLoading(false);
      }
    };

    if (callId) {
      fetchCall();
    }
  }, [callId]);

  const handleTakeover = async () => {
    try {
      const res = await api.takeCall(callId, "PJSIP/1002", "User detail view takeover");
      setHandoffMsg(res.message);
    } catch (e: any) {
      alert(`Handoff failed: ${e.message}`);
    }
  };

  const handleKeepAi = async () => {
    try {
      const res = await api.keepAi(callId, "User confirmed AI handling");
      setHandoffMsg(res.message);
    } catch (e: any) {
      alert(`Keep AI failed: ${e.message}`);
    }
  };

  const handleEndCall = async () => {
    if (!confirm("Are you sure you want to end this call?")) return;
    try {
      const res = await api.endCall(callId, "User detail view hangup");
      setHandoffMsg(res.message);
    } catch (e: any) {
      alert(`End call failed: ${e.message}`);
    }
  };

  if (!call && !loading) {
    return (
      <div className="text-center py-20">
        <p className="text-white text-lg">Call record not found</p>
        <Link href="/calls" className="text-primary hover:underline text-sm mt-2 block">
          Back to all calls
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Back Button */}
      <Link
        href="/calls"
        className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Calls History
      </Link>

      {/* Main Call Header Card */}
      <div className="glass-panel p-6 rounded-3xl space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <div className="h-14 w-14 rounded-2xl bg-primary/20 border border-primary/40 flex items-center justify-center text-primary">
              <Phone className="h-7 w-7" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-2xl font-bold text-white">
                  {call?.caller_name || call?.caller_phone}
                </h2>
                {call && <UrgencyBadge score={call.urgency_score} riskLevel={call.risk_level} />}
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">{call?.caller_phone}</p>
            </div>
          </div>

          {/* Quick Intervention Bar */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleTakeover}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-md shadow-emerald-600/30 active:scale-95"
            >
              <PhoneCall className="h-3.5 w-3.5" /> Take Call
            </button>
            <button
              onClick={handleKeepAi}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl glass-card text-xs font-bold text-slate-300 hover:text-white transition-all active:scale-95"
            >
              <UserCheck className="h-3.5 w-3.5 text-cyan-400" /> Keep AI
            </button>
            <button
              onClick={handleEndCall}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-rose-600/20 text-rose-300 hover:bg-rose-600 hover:text-white border border-rose-500/30 text-xs font-bold transition-all active:scale-95"
            >
              <PhoneOff className="h-3.5 w-3.5" /> End
            </button>
          </div>
        </div>

        {handoffMsg && (
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300">
            {handoffMsg}
          </div>
        )}

        {/* Telemetry Metadata Chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-white/10 text-xs">
          <div className="p-3 rounded-xl bg-surfaceLight/60 border border-white/5">
            <span className="text-slate-400 flex items-center gap-1.5 mb-1">
              <Clock className="h-3.5 w-3.5 text-cyan-400" /> Duration
            </span>
            <p className="font-semibold text-white">{call?.duration_seconds} seconds</p>
          </div>

          <div className="p-3 rounded-xl bg-surfaceLight/60 border border-white/5">
            <span className="text-slate-400 flex items-center gap-1.5 mb-1">
              <Globe className="h-3.5 w-3.5 text-primary" /> Language
            </span>
            <p className="font-semibold text-white uppercase font-mono">{call?.language}</p>
          </div>

          <div className="p-3 rounded-xl bg-surfaceLight/60 border border-white/5">
            <span className="text-slate-400 flex items-center gap-1.5 mb-1">
              <Shield className="h-3.5 w-3.5 text-emerald-400" /> Intent
            </span>
            <p className="font-semibold text-white capitalize">{call?.intent}</p>
          </div>

          <div className="p-3 rounded-xl bg-surfaceLight/60 border border-white/5">
            <span className="text-slate-400 flex items-center gap-1.5 mb-1">
              <FileText className="h-3.5 w-3.5 text-amber-400" /> Status
            </span>
            <p className="font-semibold text-white uppercase">{call?.status}</p>
          </div>
        </div>
      </div>

      {/* AI Call Summary */}
      {call?.summary && (
        <div className="glass-card p-6 rounded-3xl border border-primary/20 space-y-2">
          <h3 className="text-sm font-bold uppercase tracking-wider text-primary flex items-center gap-2">
            <FileText className="h-4 w-4" /> AI Interaction Summary
          </h3>
          <p className="text-sm text-slate-200 leading-relaxed italic bg-black/20 p-4 rounded-xl border border-white/5">
            &ldquo;{call.summary}&rdquo;
          </p>
        </div>
      )}

      {/* Complete Transcript Conversation Stream */}
      <div className="glass-panel p-6 rounded-3xl space-y-4">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <PhoneCall className="h-5 w-5 text-cyan-400" /> Conversational Speech Transcript
        </h3>

        <div className="space-y-1 pt-2">
          {call?.messages && call.messages.length > 0 ? (
            call.messages.map((msg) => <TranscriptBubble key={msg.id} message={msg} />)
          ) : (
            <p className="text-xs text-slate-400 py-6 text-center">No audio messages recorded.</p>
          )}
        </div>
      </div>
    </div>
  );
}
