"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api, Contact } from "@/lib/api";

export default function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [vipOnly, setVipOnly] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // New contact form state
  const [name, setName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [relationship, setRelationship] = useState("known");
  const [trustLevel, setTrustLevel] = useState("family");
  const [isVip, setIsVip] = useState(false);
  const [notes, setNotes] = useState("");

  const fetchContacts = async () => {
    setLoading(true);
    try {
      const res = await api.getContacts({
        query: search || undefined,
        is_vip: vipOnly ? true : undefined,
      });
      setContacts(res.items || []);
    } catch {
      // Demo fallback contacts if API is unreachable
      setContacts([
        {
          id: "c1",
          name: "Dr. Sarah Jenkins",
          phone_number: "+1 (555) 234-5678",
          relationship: "doctor",
          trust_level: "vip",
          is_vip: true,
          total_calls: 12,
          notes: "Primary family physician. Urgent calls should always ring through.",
        },
        {
          id: "c2",
          name: "Rajesh Sharma",
          phone_number: "+91 98765 43210",
          relationship: "family",
          trust_level: "family",
          is_vip: true,
          total_calls: 45,
          notes: "Father. AI should speak politely in Hindi/Hinglish.",
        },
        {
          id: "c3",
          name: "Amazon Logistics Courier",
          phone_number: "+91 88000 11223",
          relationship: "service",
          trust_level: "known",
          is_vip: false,
          total_calls: 4,
          notes: "Package delivery. Direct to leave with security guard at Gate 2.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContacts();
  }, [vipOnly]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchContacts();
  };

  const handleCreateContact = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createContact({
        name,
        phone_number: phoneNumber,
        relationship,
        trust_level: trustLevel,
        is_vip: isVip,
        notes,
      });
      setShowModal(false);
      setName("");
      setPhoneNumber("");
      setNotes("");
      fetchContacts();
    } catch (err: any) {
      alert("Failed to save contact: " + err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Caller Directory & Contacts</h1>
          <p className="text-sm text-slate-400">
            Manage trusted callers, relationship tiers, VIP override rules, and agent instructions.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium text-sm transition-all shadow-md shadow-indigo-500/20"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLineline="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Contact
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-4 flex flex-col md:flex-row gap-4 items-center justify-between shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex-1 w-full flex items-center gap-2">
          <div className="relative flex-1">
            <svg
              className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search by name, phone number, relationship..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-900/90 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm font-medium transition-colors"
          >
            Search
          </button>
        </form>

        <div className="flex items-center gap-2 self-end md:self-auto">
          <button
            onClick={() => setVipOnly(!vipOnly)}
            className={`px-3 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors border ${
              vipOnly
                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                : "bg-slate-900/60 text-slate-400 border-slate-700 hover:text-slate-300"
            }`}
          >
            ⭐ VIP Only
          </button>
        </div>
      </div>

      {/* Contacts Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 animate-pulse">Loading contact directory...</div>
      ) : contacts.length === 0 ? (
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-12 text-center">
          <p className="text-slate-400 font-medium">No contacts found</p>
          <p className="text-xs text-slate-500 mt-1">Add trusted callers or adjust search filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {contacts.map((contact) => (
            <Link
              key={contact.id}
              href={`/contacts/${contact.id}`}
              className="group bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 hover:border-slate-600 rounded-xl p-5 flex flex-col justify-between transition-all hover:shadow-lg"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-slate-100 group-hover:text-indigo-400 transition-colors flex items-center gap-2">
                      {contact.name}
                      {contact.is_vip && <span className="text-amber-400 text-sm">⭐</span>}
                    </h3>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">{contact.phone_number}</p>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                      contact.trust_level === "vip" || contact.trust_level === "family"
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                        : contact.trust_level === "blocked"
                        ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                        : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    }`}
                  >
                    {contact.trust_level}
                  </span>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-700/50 flex items-center justify-between text-xs text-slate-400">
                  <span className="capitalize">Relationship: <strong className="text-slate-300 font-medium">{contact.relationship}</strong></span>
                  <span>{contact.total_calls || 0} calls</span>
                </div>

                {contact.notes && (
                  <p className="mt-2 text-xs text-slate-400 line-clamp-2 italic bg-slate-900/40 p-2 rounded-lg border border-slate-800">
                    &ldquo;{contact.notes}&rdquo;
                  </p>
                )}
              </div>

              <div className="mt-4 pt-2 flex items-center justify-end text-xs text-indigo-400 font-medium group-hover:translate-x-0.5 transition-transform">
                View History & Rules &rarr;
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Add Contact Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-100">Add Trusted Contact</h2>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-200">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateContact} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Phone Number (E.164)
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. +15551234567 or +919876543210"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Relationship
                  </label>
                  <select
                    value={relationship}
                    onChange={(e) => setRelationship(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="family">Family</option>
                    <option value="friend">Friend</option>
                    <option value="doctor">Doctor</option>
                    <option value="colleague">Colleague</option>
                    <option value="service">Service/Delivery</option>
                    <option value="unknown">Unknown</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Trust Level
                  </label>
                  <select
                    value={trustLevel}
                    onChange={(e) => setTrustLevel(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="family">Family (High Trust)</option>
                    <option value="vip">VIP (Always Bypass)</option>
                    <option value="known">Known (Normal AI)</option>
                    <option value="blocked">Blocked (Auto Reject)</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="is_vip_check"
                  checked={isVip}
                  onChange={(e) => setIsVip(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
                <label htmlFor="is_vip_check" className="text-sm text-slate-300 select-none">
                  Mark as VIP (Priority Notification)
                </label>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Custom AI Handling Instructions
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. Always greet in Hindi, transfer immediately if regarding medical appointments."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors shadow-md shadow-indigo-600/20"
                >
                  Save Contact
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
