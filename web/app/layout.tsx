import type { Metadata } from "next";
import { Bangers, Bricolage_Grotesque, Luckiest_Guy, Space_Mono } from "next/font/google";
import "./globals.css";
import { Masthead } from "@/components/masthead";

// Comic-book type system: a chunky logo face, a lettering face for captions
// and sound effects, a friendly grotesk for balloons, a mono for file paths.
const logo = Luckiest_Guy({ subsets: ["latin"], weight: "400", variable: "--font-logo" });
const sfx = Bangers({ subsets: ["latin"], weight: "400", variable: "--font-sfx" });
const body = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-body" });
const mono = Space_Mono({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Ask Iannis! · Iannis Vasselet",
  description:
    "The only profile that answers back. Ask anything about Iannis Vasselet; every answer comes with an editor's note pointing to its source.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${logo.variable} ${sfx.variable} ${body.variable} ${mono.variable}`}>
      <body>
        <div className="app">
          <Masthead />
          {children}
        </div>
      </body>
    </html>
  );
}
