import type { NextConfig } from "next";

// The browser always calls /api/v1 on the web app's own origin; Next.js forwards it to the
// FastAPI backend. One origin means no CORS, first-party refresh cookies, and nothing for
// ad/privacy blockers to block. In production Nginx does the same job (infra/nginx).
const API_PROXY_TARGET = (process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000").replace(/\/$/, "");

// In development Next.js only serves its scripts to pages opened on localhost. Opening the app
// via another address (127.0.0.1, your LAN IP, Docker's 192.168.65.1) loads the HTML but not
// the JavaScript, so nothing on the page responds. Allow loopback and private-network hosts;
// add more with DEV_ALLOWED_ORIGINS=host1,host2 in .env.local. Dev-server only.
const DEV_ALLOWED_ORIGINS = [
  "127.0.0.1",
  "192.168.*.*",
  "10.*.*.*",
  ...(process.env.DEV_ALLOWED_ORIGINS ?? "")
    .split(",")
    .map((h) => h.trim())
    .filter(Boolean),
];

const nextConfig: NextConfig = {
  allowedDevOrigins: DEV_ALLOWED_ORIGINS,
  output: "standalone", // for the Docker image
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${API_PROXY_TARGET}/api/v1/:path*` }];
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
