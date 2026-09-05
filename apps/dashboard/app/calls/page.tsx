"use client";

import React, { useEffect, useState } from "react";
import { api, Call } from "@/lib/api";
import { CallItem } from "@/components/CallItem";
import { Search, Filter, PhoneCall, RefreshCw } from "lucide-react";

export default function CallsPage() {
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIntent, setSelectedIntent] = useState<string>("all");

  const intents = [
    "all",
    "delivery",
    "recruiter",
    "personal",
    "emergency",
    "spam",
    "banking",
    "service",
  ];

  const fetchCalls = async () => {
    try {
      setLoading(true);
      const data = await api.getCalls({ limit: 50 });
      setCalls(data.items || []);
    } catch (e) {
      console.error("Failed to load calls:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalls();
  }, []);

  const filteredCalls = calls.filter((c) => {
    const matchesSearch =
      !searchQuery ||
      c.caller_phone.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.caller_name && c.caller_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.summary && c.summary.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesIntent =
      selectedIntent === "all" || c.intent.toLowerCase() === selectedIntent.toLowerCase();

    return matchesSearch && matchesIntent;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Call Records</h2>
          <p className="text-slate-400 text-sm mt-1">
            Browse complete transcripts, caller intents, urgency scores, and historical summaries.
          </p>
        </div>

        <button
          onClick={fetchCalls}
          className="flex items-center gap-2 px-4 py-2 rounded-xl glass-card text-xs font-semibold text-slate-300 hover:text-white transition-all"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="glass-panel p-4 rounded-2xl flex flex-col md:flex-row items-center gap-4 justify-between">
        <div className="relative w-full md:w-96">
          <Search className="h-4 w-4 text-slate-400 absolute left-3 top-3.5" />
          <input
            type="text"
            placeholder="Search by phone, caller name, or keyword..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-surfaceLight border border-white/10 text-white placeholder-slate-400 text-sm focus:outline-none focus:border-primary transition-all"
          />
        </div>

        {/* Intent category pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto pb-1 md:pb-0">
          <Filter className="h-4 w-4 text-slate-400 mr-1 shrink-0" />
          {intents.map((intent) => (
            <button
              key={intent}
              onClick={() => setSelectedIntent(intent)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize shrink-0 transition-all ${
                selectedIntent === intent
                  ? "bg-primary text-white shadow-md shadow-primary/30"
                  : "bg-surfaceLight/80 text-slate-400 hover:text-white border border-white/5"
              }`}
            >
              {intent}
            </button>
          ))}
        </div>
      </div>

      {/* Call List */}
      <div className="space-y-3">
        {filteredCalls.length > 0 ? (
          filteredCalls.map((call) => <CallItem key={call.id} call={call} />)
        ) : (
          <div className="glass-card p-12 rounded-2xl text-center">
            <PhoneCall className="h-12 w-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-300 font-semibold text-lg">No calls match your criteria</p>
            <p className="text-slate-500 text-xs mt-1">Try adjusting your search query or intent filter.</p>
          </div>
        )}
      </div>
    </div>
  );
}
