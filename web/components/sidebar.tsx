"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PROFILE } from "@/lib/profile";

const NAV = [
  { href: "/", label: "Ask", icon: "◇" },
  { href: "/job-fit", label: "Job fit", icon: "⊹" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sidebar">
      <div style={{ marginBottom: 22 }}>
        <div className="eyebrow" style={{ marginBottom: 6 }}>Candidate OS</div>
        <div className="display" style={{ fontSize: 22 }}>{PROFILE.name}</div>
        <div style={{ color: "var(--muted)", fontSize: 12.5, marginTop: 2 }}>
          {PROFILE.title}
        </div>
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-item ${pathname === item.href ? "active" : ""}`}
          >
            <span className="mono" style={{ color: "var(--ember)" }}>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 1 }}>
        <div className="eyebrow" style={{ padding: "0 11px 6px" }}>Elsewhere</div>
        <a className="side-link" href={PROFILE.links.github} target="_blank" rel="noreferrer">↗ GitHub</a>
        <a className="side-link" href={PROFILE.links.linkedin} target="_blank" rel="noreferrer">↗ LinkedIn</a>
        <a className="side-link" href={PROFILE.links.portfolio} target="_blank" rel="noreferrer">↗ Portfolio</a>
        <a className="side-link" href={PROFILE.links.email}>↗ Email</a>
      </div>
    </aside>
  );
}
