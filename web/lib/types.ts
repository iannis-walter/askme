export type SourceKind =
  | "bio"
  | "experience"
  | "skills"
  | "faq"
  | "project"
  | "role";

export interface Source {
  id: string;
  title: string;
  kind: SourceKind;
  score?: number;
}

export interface AgentStep {
  tool: string;
  args: Record<string, unknown>;
  ok: boolean;
  error?: string | null;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  streaming?: boolean;
  steps?: AgentStep[];
}

export interface JobFitResult {
  summary: string;
  strengths: string[];
  gaps: string[];
  relevant_projects: string[];
  pitch: string;
  sources: Source[];
}
