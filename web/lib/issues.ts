import type { Source } from "@/lib/types";

// The comic-book metaphor: every project is an issue of "Ask Iannis!", and
// every citation is an editor's note pointing back to where it happened.
export interface Issue {
  slug: string;
  no: string;
  title: string;
  tagline: string;
  art: string;
}

export const ISSUES: Record<string, Issue> = {
  aria: { slug: "aria", no: "#01", title: "Aria", tagline: "Safe places, lit up!", art: "/art/cover-aria.png" },
  "ask-me-candidate-os": { slug: "ask-me-candidate-os", no: "#02", title: "Ask Me", tagline: "Talks back!", art: "/art/cover-askme.png" },
  flightdynamics: { slug: "flightdynamics", no: "#03", title: "Flight Dynamics", tagline: "Six degrees of freedom!", art: "/art/cover-flightdynamics.png" },
  hyperion: { slug: "hyperion", no: "#04", title: "Hyperion", tagline: "Alerts that talk!", art: "/art/cover-hyperion.png" },
  sillage: { slug: "sillage", no: "#05", title: "Sillage", tagline: "Book the expedition!", art: "/art/cover-sillage.png" },
  vigie: { slug: "vigie", no: "#06", title: "Vigie", tagline: "Eyes on the sea!", art: "/art/cover-vigie.png" },
};

// Back issues shown on the cover, in reading order.
export const FEATURED_ISSUES = ["ask-me-candidate-os", "hyperion", "vigie"].map((s) => ISSUES[s]);

export function issueFor(source: Source): Issue | undefined {
  return source.kind === "project" ? ISSUES[source.id] : undefined;
}

// Job-fit returns project names as free text; match them back to an issue.
export function issueByName(name: string): Issue | undefined {
  const n = name.toLowerCase();
  return Object.values(ISSUES).find(
    (i) => n.includes(i.title.toLowerCase()) || n.includes(i.slug) || i.title.toLowerCase().includes(n)
  );
}

export function fileLabel(s: Source): string {
  switch (s.kind) {
    case "bio":
      return "bio.json";
    case "skills":
      return "skills.json";
    case "experience":
      return "experience.json";
    case "faq":
      return "faq.json";
    case "project":
      return `projects/${s.id}.md`;
    case "role":
      return `roles/${s.id}.md`;
    default:
      return s.id;
  }
}

// "*See Issue #04: Hyperion! —Ed." for projects, "the Files" for everything else.
export function noteText(s: Source): string {
  const issue = issueFor(s);
  if (issue) return `See Issue ${issue.no}: ${issue.title}!`;
  if (s.kind === "role") return "See the case file on this role!";
  if (s.kind === "faq") return "See the FAQ!";
  if (s.kind === "experience") return `See the Files: ${s.title}!`;
  return `See the Files: ${s.kind === "bio" ? "the origin story" : "the skills sheet"}!`;
}

export function noteMarker(i: number): string {
  return i < 3 ? "*".repeat(i + 1) : ["†", "‡", "§", "¶"][(i - 3) % 4];
}
