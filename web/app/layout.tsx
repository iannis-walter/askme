import type { Metadata } from "next";
import { Fraunces, Newsreader, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";

// Editorial dossier type system: a characterful display serif, a readable body
// serif, and a mono for captions / source credits.
const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
});
const serif = Newsreader({
  subsets: ["latin"],
  variable: "--font-serif",
  weight: ["400", "500"],
  style: ["normal", "italic"],
});
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Ask Me — Iannis Vasselet",
  description:
    "A conversational, source-grounded briefing on the candidate. Ask anything; every answer cites where it came from.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${display.variable} ${serif.variable} ${mono.variable}`}>
      <body>
        <div className="app-grid">
          <Sidebar />
          {children}
        </div>
      </body>
    </html>
  );
}
