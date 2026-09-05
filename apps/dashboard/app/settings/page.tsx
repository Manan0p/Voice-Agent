"use client";

import React, { useState } from "react";

export default function SettingsPage() {
  const [voice, setVoice] = useState("af_bella");
  const [speed, setSpeed] = useState("1.0");
  const [sttModel, setSttModel] = useState("faster-whisper-base.en");
  const [llmModel, setLlmModel] = useState("gemini-2.0-flash");
  const [callForwardingCarrier, setCallForwardingCarrier] = useState("Jio / Airtel (*21*)");
  const [telegramNotifications, setTelegramNotifications] = useState(true);
  const [telegramChatId, setTelegramChatId] = useState("89234198");
  const [asteriskHost, setAsteriskHost] = useState("127.0.0.1:8088");
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">System & Engine Settings</h1>
        <p className="text-sm text-slate-400">
          Configure local voice models, Asterisk PBX connection, carrier forwarding hooks, and Telegram alerts.
        </p>
      </div>

      {saved && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-4 rounded-xl text-sm flex items-center gap-2">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Configuration parameters successfully saved to environment!
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Voice & Speech Synthesis (Kokoro) */}
        <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-slate-200 border-b border-slate-700/60 pb-3 flex items-center gap-2">
            <span>🎙️</span> Kokoro-82M TTS & Speech Settings
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Voice Profile
              </label>
              <select
                value={voice}
                onChange={(e) => setVoice(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="af_bella">af_bella (American Female - Crisp & Natural)</option>
                <option value="af_sarah">af_sarah (American Female - Warm Professional)</option>
                <option value="am_adam">am_adam (American Male - Friendly Assistant)</option>
                <option value="am_michael">am_michael (American Male - Deep Corporate)</option>
                <option value="bf_emma">bf_emma (British Female - Polite Receptionist)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Speaking Rate Speed Multiplier
              </label>
              <select
                value={speed}
                onChange={(e) => setSpeed(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="0.9">0.9x (Deliberate / Calm)</option>
                <option value="1.0">1.0x (Natural Default)</option>
                <option value="1.1">1.1x (Brisk Professional)</option>
                <option value="1.2">1.2x (Fast Phone Flow)</option>
              </select>
            </div>
          </div>
        </div>

        {/* STT & LLM Engines */}
        <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-slate-200 border-b border-slate-700/60 pb-3 flex items-center gap-2">
            <span>🧠</span> STT & LLM Pipeline Models
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Speech-to-Text Engine
              </label>
              <select
                value={sttModel}
                onChange={(e) => setSttModel(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="faster-whisper-base.en">faster-whisper (base.en - Fast int8)</option>
                <option value="faster-whisper-small">faster-whisper (small - Multilingual)</option>
                <option value="faster-whisper-medium">faster-whisper (medium - Accurate)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Decision & Reasoning LLM
              </label>
              <select
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="gemini-2.0-flash">Google Gemini 2.0 Flash (Sub-second streaming)</option>
                <option value="gemini-1.5-pro">Google Gemini 1.5 Pro (Deep reasoning)</option>
                <option value="ollama-llama-3.1-8b">Local Ollama Llama 3.1 8B (100% Offline)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Asterisk Telephony & SIP Trunking */}
        <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-slate-200 border-b border-slate-700/60 pb-3 flex items-center gap-2">
            <span>📞</span> Asterisk PBX & Mobile Call Forwarding
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Asterisk ARI HTTP Host
              </label>
              <input
                type="text"
                value={asteriskHost}
                onChange={(e) => setAsteriskHost(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Forwarding Carrier Profile (Diversion Header)
              </label>
              <select
                value={callForwardingCarrier}
                onChange={(e) => setCallForwardingCarrier(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="Jio / Airtel (*21*)">Airtel / Jio / Vodafone (*21* Mobile Forwarding)</option>
                <option value="AT&T / Verizon (*72)">AT&T / Verizon / T-Mobile (*72 / *67)</option>
                <option value="Direct DID Trunk">Direct DID Trunk (Standard From / To headers)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Telegram Notifications */}
        <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-slate-200 border-b border-slate-700/60 pb-3 flex items-center gap-2">
            <span>💬</span> Telegram Realtime Call Alerts & Takeover Bot
          </h2>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="tg_toggle"
              checked={telegramNotifications}
              onChange={(e) => setTelegramNotifications(e.target.checked)}
              className="w-5 h-5 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="tg_toggle" className="text-sm text-slate-300 select-none cursor-pointer">
              Send Telegram notification cards with Take Call / Keep AI inline buttons on incoming calls
            </label>
          </div>

          {telegramNotifications && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Telegram User Chat ID
              </label>
              <input
                type="text"
                value={telegramChatId}
                onChange={(e) => setTelegramChatId(e.target.value)}
                placeholder="e.g. 123456789"
                className="w-full md:w-1/2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
          )}
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition-all shadow-md shadow-indigo-600/20"
          >
            Save All Preferences
          </button>
        </div>
      </form>
    </div>
  );
}
