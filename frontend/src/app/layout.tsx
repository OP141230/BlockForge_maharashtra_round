import React from "react";
import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/sidebar";

export const metadata: Metadata = {
  title: "BLACKBOX: AI Agent Flight Recorder",
  description: "Flight recorder plus investigation system for autonomous AI agents.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex h-screen overflow-hidden bg-bg text-text-primary antialiased">
        <Sidebar />
        <main className="flex-1 flex flex-col h-screen overflow-y-auto relative">
          {children}
        </main>
      </body>
    </html>
  );
}
