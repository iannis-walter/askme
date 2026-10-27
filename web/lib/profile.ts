// Surface-level profile facts used for chrome (masthead, cover).
// The substantive content lives in /content and is served by the backend.
export const PROFILE = {
  name: "Iannis Vasselet",
  title: "Lead Full-Stack Engineer · Applied AI",
  subtitle: "A briefing you can question.",
  links: {
    github: "https://github.com/iannis-walter",
    linkedin: "https://www.linkedin.com/in/iannis-vasselet/",
    portfolio: "https://portfolio-v2-rouge-six.vercel.app/",
    email: "mailto:iannisvasselet@gmail.com",
  },
};

// Files in /content the assistant can cite (bio, experience, faq, skills,
// six projects, one role note). Shown on the cover burst.
export const SOURCES_ON_FILE = 11;

export const SUGGESTED_PROMPTS = [
  { label: "For a CTO", teaser: "For a CTO: the whole guy in 5 lines!", text: "Summarize this candidate for a CTO in 5 lines." },
  { label: "Applied AI", teaser: "Applied AI: the projects that prove it!", text: "Which projects best prove his applied-AI ability?" },
  { label: "Full-stack", teaser: "Full-stack: front AND back, for real?", text: "What proves his full-stack ability across front and back?" },
  { label: "Fit · Mistral", teaser: "Crossover: Iannis × Mistral!", text: "Why could he be a fit for Mistral's Applied AI Engineer role?" },
];
