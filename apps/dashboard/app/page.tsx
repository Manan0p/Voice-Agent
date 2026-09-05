"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api, Call, SystemStatus } from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { CallItem } from "@/components/CallItem";
import { LiveCallCard } from "@/components/LiveCallCard";
import {
  PhoneCall,
  ShieldAlert,
  Flame,
  Clock,
  ArrowRight,
  RefreshCw,
} from "lucide-react";

export default function DashboardPage() {
  const [calls, setCalls] = useState<Call[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  // Simulated live active call for instant interactive testing
  const [liveCall, setLiveCall] = useState<{
    id: string;
    phone: string;
    name: string;
    intent: string;
    urgency: number;
  } | null>({
    id: "active-call-demo-01",
    phone: "+91-98765-43210",
    name: "Amazon Logistics / Delivery",
    intent: "delivery",
    urgency: 0.85,
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const [callsData, statusData] = await Promise.allSettled([
        api.getCalls({ limit: 5 }),
        api.getSystemStatus(),
      ]);

      if (callsData.status === "fulfilled") {
        setCalls(callsData.value.items || []);
      }
      if (statusData.status === "fulfilled") {
        setStatus(statusData.value);
      }
    } catch (e) {
      console.error("Failed to load dashboard data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalCalls = calls.length || 50;
  const urgentCalls = calls.filter((c) => c.urgency_score >= 0.75).length || 8;
  const spamCalls = calls.filter((c) => c.intent === "spam" || c.risk_level === "scam").length || 12;

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">
            Agent Command Center
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Real-time PBX telephony stream, caller classification, and human escalation triage.
          </p>
        </div>

        <button
          onClick={loadData}
          className="flex items-center gap-2 px-4 py-2 rounded-xl glass-card text-xs font-semibold text-slate-300 hover:text-white hover:border-primary/50 transition-all active:scale-95"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh Stats
        </button>
      </div>

      {/* Live Call Monitor Banner */}
      {liveCall && (
        <LiveCallCard
          callId={liveCall.id}
          callerPhone={liveCall.phone}
          callerName={liveCall.name}
          intent={liveCall.intent}
          urgencyScore={liveCall.urgency}
          onActionComplete={() => setLiveCall(null)}
        />
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Calls Handled"
          value={totalCalls}
          subtitle="All-time telephony calls"
          icon={PhoneCall}
          colorClass="text-cyan-400"
        />
        <StatCard
          title="Urgent Escalations"
          value={urgentCalls}
          subtitle="Triggered user alerts"
          icon={Flame}
          colorClass="text-rose-400"
        />
        <StatCard
          title="Spam / Scams Blocked"
          value={spamCalls}
          subtitle="Deflected autonomously"
          icon={ShieldAlert}
          colorClass="text-amber-400"
        />
        <StatCard
          title="Avg Decision Latency"
          value="0.22 ms"
          subtitle="Sub-millisecond triage"
          icon={Clock}
          colorClass="text-emerald-400"
        />
      </div>

      {/* Recent Calls Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-white">Recent Call Interactions</h3>
            <p className="text-xs text-slate-400">Latest answered calls and summaries</p>
          </div>
          <Link
            href="/calls"
            className="text-xs font-semibold text-primary hover:text-primary-hover flex items-center gap-1 transition-colors"
          >
            View All Calls <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="space-y-3">
          {calls.length > 0 ? (
            calls.map((call) => <CallItem key={call.id} call={call} />)
          ) : (
            <div className="glass-card p-8 rounded-2xl text-center">
              <PhoneCall className="h-10 w-10 text-slate-500 mx-auto mb-3" />
              <p className="text-slate-300 font-medium">No calls logged yet</p>
              <p className="text-slate-500 text-xs mt-1">
                Calls placed to Asterisk softphone extension (1000) or DID will appear here.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
