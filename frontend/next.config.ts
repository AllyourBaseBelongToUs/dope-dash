import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Enable strict ESLint checking - fail build on errors
  eslint: {
    ignoreDuringBuilds: false, // FIXED: Now fails build on ESLint errors
  },
  // Enable strict TypeScript checking - fail build on type errors
  typescript: {
    ignoreBuildErrors: false, // FIXED: Now fails build on TypeScript errors
  },
};

export default nextConfig;
