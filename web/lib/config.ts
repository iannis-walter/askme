// Server-only. The browser never sees the backend URL or talks to it directly;
// all calls go through Next.js route handlers that proxy to this.
export const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
