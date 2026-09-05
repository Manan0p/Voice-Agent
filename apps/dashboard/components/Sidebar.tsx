"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  PhoneCall,
  Users,
  BookOpen,
  Settings,
  Activity,
  ShieldCheck,
  Radio,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { label: "Overview", href: "/", icon: Activity },
    { label: "Calls History", href: "/calls", icon: PhoneCall },
    { label: "Contacts Book", href: "/contacts", icon: Users },
    { label: "Knowledge RAG", href: "/knowledge", icon: BookOpen },
    { label: "Settings", href: "/settings", icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-white/10 bg-surface/80 backdrop-blur-xl flex flex-col justify-between h-screen sticky top-0">
      <div>
        {/* Brand */}
        <div className="p-6 border-b border-white/10 flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-primary to-accent-cyan flex items-center justify-center shadow-lg shadow-primary/30">
            <Radio className="h-5 w-5 text-white animate-pulse" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-wide">
              VoiceAgent<span className="text-primary">.ai</span>
            </h1>
            <p className="text-xs text-slate-400 font-mono">Personal AI PBX</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-primary text-white shadow-lg shadow-primary/30 font-semibold"
                    : "text-slate-300 hover:text-white hover:bg-white/5"
                }`}
              >
                <Icon className={`h-5 w-5 ${isActive ? "text-white" : "text-slate-400"}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* System Status Footer */}
      <div className="p-4 border-t border-white/10 m-4 rounded-xl bg-surfaceLight/50 border border-white/5">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
          <span className="flex items-center gap-1.5 font-medium text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
            Asterisk PBX Online
          </span>
          <ShieldCheck className="h-4 w-4 text-slate-400" />
        </div>
        <p className="text-xs text-slate-400">
          STT: Faster-Whisper | TTS: Kokoro
        </p>
      </div>
    </aside>
  );
}
