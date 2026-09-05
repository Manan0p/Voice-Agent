import React from "react";
import { Message } from "@/lib/api";
import { Bot, User, PhoneCall } from "lucide-react";

interface TranscriptBubbleProps {
  message: Message;
}

export function TranscriptBubble({ message }: TranscriptBubbleProps) {
  const isAgent = message.speaker === "agent";
  const isUser = message.speaker === "user";

  let align = "justify-start";
  let bg = "bg-surfaceLight/80 border-white/10 text-slate-200";
  let icon = <PhoneCall className="h-4 w-4 text-cyan-400" />;
  let label = "Caller";

  if (isAgent) {
    align = "justify-end";
    bg = "bg-primary/20 border-primary/30 text-white shadow-lg shadow-primary/10";
    icon = <Bot className="h-4 w-4 text-primary" />;
    label = "AI Assistant";
  } else if (isUser) {
    align = "justify-end";
    bg = "bg-emerald-500/20 border-emerald-500/30 text-emerald-100";
    icon = <User className="h-4 w-4 text-emerald-400" />;
    label = "You (Human Takeover)";
  }

  return (
    <div className={`flex gap-3 my-3 ${align}`}>
      {!isAgent && !isUser && (
        <div className="h-8 w-8 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center shrink-0 mt-1">
          {icon}
        </div>
      )}

      <div className={`max-w-[75%] rounded-2xl p-4 border ${bg}`}>
        <div className="flex items-center justify-between gap-4 mb-1 text-xs">
          <span className="font-semibold text-slate-300">{label}</span>
          <span className="text-slate-400 font-mono text-[10px]">
            {message.timestamp ? new Date(message.timestamp).toLocaleTimeString() : ""}
          </span>
        </div>
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        {message.language && (
          <span className="inline-block mt-2 text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-black/30 text-slate-400">
            {message.language}
          </span>
        )}
      </div>

      {(isAgent || isUser) && (
        <div className="h-8 w-8 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center shrink-0 mt-1">
          {icon}
        </div>
      )}
    </div>
  );
}
