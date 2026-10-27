"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PROFILE } from "@/lib/profile";

const NAV = [
  { href: "/", label: "Ask" },
  { href: "/job-fit", label: "Job fit" },
];

const LINKS = [
  { href: PROFILE.links.github, label: "GitHub", external: true },
  { href: PROFILE.links.linkedin, label: "LinkedIn", external: true },
  { href: PROFILE.links.portfolio, label: "Portfolio", external: true },
  { href: PROFILE.links.email, label: "Email", external: false },
];

// The publisher bar above every page: logo, issue folio, the two sections
// as tabs, and where else to find the hero.
export function Masthead() {
  const pathname = usePathname();
  return (
    <header className="masthead">
      <Link href="/" className="mast-logo" aria-label="Ask Iannis! home">
        Ask Iannis!
      </Link>
      <span className="mast-folio">Issue #1 · Oct 2026 · {PROFILE.title}</span>
      <nav className="mast-tabs" aria-label="Sections">
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="mast-tab"
            aria-current={pathname === item.href ? "page" : undefined}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <nav className="mast-links" aria-label="Elsewhere">
        {LINKS.map((l) => (
          <a
            key={l.label}
            href={l.href}
            {...(l.external ? { target: "_blank", rel: "noreferrer" } : {})}
          >
            {l.label}
          </a>
        ))}
      </nav>
    </header>
  );
}
