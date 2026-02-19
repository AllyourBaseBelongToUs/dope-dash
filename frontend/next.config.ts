import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Note: ESLint config removed in Next.js 16 - use eslint.config.js instead
  // Enable strict TypeScript checking - fail build on type errors
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
