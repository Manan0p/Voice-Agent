import React from "react";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata = {
  title: "Personal AI Caller — Web Dashboard",
  description: "Self-Hosted Privacy-First Voice Agent PBX & Call Assistant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="flex min-h-screen bg-background text-slate-100">
        <Sidebar />
        <main className="flex-1 p-8 overflow-y-auto max-w-7xl mx-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
