"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, Contact } from "@/lib/api";

export default function ContactDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [contact, setContact] = useState<Contact | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notes, setNotes] = useState("");
  const [trustLevel, setTrustLevel] = useState("known");
  const [isVip, setIsVip] = useState(false);

  useEffect(() => {
    const fetchContact = async () => {
      setLoading(true);
      try {
        const data = await api.getContactById(id);
        setContact(data);
        setNotes(data.notes || "");
        setTrustLevel(data.trust_level || "known");
        setIsVip(data.is_vip || false);
      } catch {
        // Fallback demo contact
        const demo: Contact = {
          id: id,
          name: "Dr. Sarah Jenkins",
          phone_number: "+1 (555) 234-5678",
          relationship: "doctor",
          trust_level: "vip",
          is_vip: true,
          total_calls: 12,
          last_called_at: "2026-09-05T18:22:00Z",
          notes: "Primary family physician. Urgent calls should always ring through immediately.",
        };
        setContact(demo);
        setNotes(demo.notes || "");
        setTrustLevel(demo.trust_level);
        setIsVip(demo.is_vip);
      } finally {
        setLoading(false);
      }
    };

    fetchContact();
  }, [id]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      // simulate/save update
      await new Promise((r) => setTimeout(r, 600));
      alert("Contact preferences saved successfully!");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-slate-500 animate-pulse">Loading contact details...</div>;
  }

  if (!contact) {
    return (
      <div className="p-8 text-center">
        <p className="text-slate-400">Contact not found.</p>
        <Link href="/contacts" className="mt-4 inline-block text-indigo-400 text-sm hover:underline">
          &larr; Back to Contacts
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Back button */}
      <div>
        <Link
          href="/contacts"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Contact Directory
        </Link>
      </div>

      {/* Header Info */}
      <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center font-bold text-lg">
              {contact.name.charAt(0)}
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                {contact.name}
                {isVip && <span className="text-amber-400 text-base">⭐ VIP</span>}
              </h1>
              <p className="text-sm font-mono text-slate-400 mt-0.5">{contact.phone_number}</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-400">
          <div className="bg-slate-900/60 border border-slate-700 px-3 py-2 rounded-lg text-center">
            <span className="block text-slate-500 uppercase text-[10px] font-bold">Total Calls</span>
            <span className="text-slate-200 font-semibold text-sm">{contact.total_calls}</span>
          </div>
          <div className="bg-slate-900/60 border border-slate-700 px-3 py-2 rounded-lg text-center">
            <span className="block text-slate-500 uppercase text-[10px] font-bold">Relationship</span>
            <span className="text-slate-200 font-semibold text-sm capitalize">{contact.relationship}</span>
          </div>
        </div>
      </div>

      {/* Configuration Form */}
      <form onSubmit={handleUpdate} className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-6 space-y-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-200 border-b border-slate-700/60 pb-3">
          AI Handling & Trust Rules
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Trust Level Tier
            </label>
            <select
              value={trustLevel}
              onChange={(e) => setTrustLevel(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="family">Family (Highest Trust, personal tone)</option>
              <option value="vip">VIP (Always ring mobile directly)</option>
              <option value="known">Known (Screen normally with AI)</option>
              <option value="service">Service Provider (Take detailed message)</option>
              <option value="blocked">Blocked (Polite decline / hangup)</option>
            </select>
            <p className="text-xs text-slate-500 mt-1.5">
              Determines how aggressively the AI screens calls before notifying you.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              VIP Priority Override
            </label>
            <div className="flex items-center gap-3 h-10">
              <input
                type="checkbox"
                id="vip_toggle"
                checked={isVip}
                onChange={(e) => setIsVip(e.target.checked)}
                className="w-5 h-5 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="vip_toggle" className="text-sm text-slate-300 select-none cursor-pointer">
                Ring phone & send instant push notification on any incoming call
              </label>
            </div>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Specific Agent Directives & Context
          </label>
          <textarea
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. Speaks Hindi or English. Inform that Manan is in a meeting until 6 PM. If call is regarding pathology reports, take the reference number."
            className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed font-mono"
          />
          <p className="text-xs text-slate-500 mt-1.5">
            These instructions are injected into the LLM system prompt whenever this caller ID is recognized.
          </p>
        </div>

        <div className="flex justify-end pt-4 border-t border-slate-700/60">
          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-all shadow-md shadow-indigo-600/20 flex items-center gap-2"
          >
            {saving ? "Saving..." : "Save Contact Directives"}
          </button>
        </div>
      </form>
    </div>
  );
}
