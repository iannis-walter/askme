// Surface-level profile facts used for chrome (sidebar, header).
// The substantive content lives in /content and is served by the backend.
export const PROFILE = {
  name: "Iannis Vasselet",
  title: "Lead Full-Stack Engineer · Applied AI",
  subtitle: "Candidate briefing — ask anything, every answer is sourced.",
  links: {
    github: "https://github.com/IannisVasselet",
    linkedin: "https://www.linkedin.com/in/iannisvasselet",
    portfolio: "https://portfolio-creative.vercel.app",
    email: "mailto:iannis.taioglou@gmail.com",
  },
};

export const SUGGESTED_PROMPTS = [
  { label: "For a CTO", text: "Summarize this candidate for a CTO in 5 lines." },
  { label: "Applied AI", text: "Which projects best prove his applied-AI ability?" },
  { label: "Full-stack", text: "What proves his full-stack ability across front and back?" },
  { label: "Fit · Mistral", text: "Why could he be a fit for Mistral's Applied AI Engineer role?" },
];
