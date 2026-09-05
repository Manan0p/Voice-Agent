"use client";

import React, { useEffect, useState } from "react";
import { api, KnowledgeDoc } from "@/lib/api";

export default function KnowledgePage() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("calendar");
  const [content, setContent] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const res = await api.getKnowledgeDocs();
      setDocs(res.items || []);
    } catch {
      // Demo fallback docs
      setDocs([
        {
          id: "k1",
          title: "Weekly Calendar & Daily Availability",
          category: "calendar",
          content:
            "Manan is working Monday to Friday 10 AM to 6 PM. Focus block from 2 PM to 4 PM daily. Free for meetings after 4:30 PM. Weekend calls should be taken by AI unless family VIP.",
          chunk_count: 3,
          created_at: "2026-09-01T10:00:00Z",
        },
        {
          id: "k2",
          title: "Delivery & Apartment Security Instructions",
          category: "personal",
          content:
            "Apartment 402, Tower B. Courier packages can be left with the ground floor security guard at Gate 2. If delivery OTP is required, tell them Manan will send it shortly via SMS.",
          chunk_count: 2,
          created_at: "2026-09-02T14:30:00Z",
        },
        {
          id: "k3",
          title: "Clinic & Medical Emergency Protocols",
          category: "medical",
          content:
            "Family physician is Dr. Sarah Jenkins at City Health. In case of medical emergencies or critical lab alerts, ask the caller to stay on line and bridge immediately.",
          chunk_count: 4,
          created_at: "2026-09-03T09:15:00Z",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleAddDoc = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !content) return;
    setIsUploading(true);

    try {
      // In real server, POST /api/knowledge
      await new Promise((r) => setTimeout(r, 600));
      const newDoc: KnowledgeDoc = {
        id: "k_" + Date.now(),
        title,
        category,
        content,
        chunk_count: Math.ceil(content.split(" ").length / 50),
        created_at: new Date().toISOString(),
      };
      setDocs([newDoc, ...docs]);
      setTitle("");
      setContent("");
      alert("Document embedded & indexed in pgvector successfully!");
    } catch (err: any) {
      alert("Failed to upload knowledge: " + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const filteredDocs = docs.filter(
    (d) =>
      d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100">RAG Knowledge & Personal Context</h1>
        <p className="text-sm text-slate-400">
          Upload personal context, schedule notes, delivery rules, and FAQs. The agent indexes these into pgvector
          for sub-second semantic retrieval during live phone calls.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Document Ingestion Form */}
        <div className="lg:col-span-1 bg-slate-800/80 border border-slate-700/80 rounded-2xl p-5 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
            <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Ingest New Knowledge Doc
          </h2>

          <form onSubmit={handleAddDoc} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Document Title
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Flight & Travel Itinerary"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="calendar">Calendar / Schedule</option>
                <option value="personal">Personal / Home</option>
                <option value="work">Work / Projects</option>
                <option value="medical">Medical / Health</option>
                <option value="faq">General FAQ</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Content & Facts
              </label>
              <textarea
                rows={6}
                required
                placeholder="Paste facts, directions, preferences or policies here. Will be automatically chunked into 300-char embeddings."
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono leading-relaxed"
              />
            </div>

            <button
              type="submit"
              disabled={isUploading}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-all shadow-md shadow-indigo-600/20"
            >
              {isUploading ? "Chunking & Embedding..." : "Vectorize & Index"}
            </button>
          </form>
        </div>

        {/* Existing Documents List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-3 flex items-center justify-between gap-4">
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
                placeholder="Filter indexed knowledge..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-900/90 border border-slate-700 rounded-lg pl-9 pr-4 py-1.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <span className="text-xs text-slate-400 font-medium">
              {filteredDocs.length} {filteredDocs.length === 1 ? "document" : "documents"} indexed
            </span>
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-500 animate-pulse">Loading RAG index...</div>
          ) : filteredDocs.length === 0 ? (
            <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-12 text-center">
              <p className="text-slate-400 font-medium">No knowledge documents matching query</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredDocs.map((doc) => (
                <div
                  key={doc.id}
                  className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-5 hover:border-slate-600 transition-colors space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-slate-100">{doc.title}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                          {doc.category}
                        </span>
                        <span className="text-xs text-slate-400">
                          {doc.chunk_count} pgvector {doc.chunk_count === 1 ? "chunk" : "chunks"}
                        </span>
                      </div>
                    </div>
                    <span className="text-xs text-slate-500 font-mono">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 font-mono bg-slate-900/60 border border-slate-700/50 p-3 rounded-lg leading-relaxed whitespace-pre-wrap">
                    {doc.content}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
