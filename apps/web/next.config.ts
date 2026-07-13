import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  eslint: {
    // Dedicated `pnpm run lint` is the CI gate; avoid Next's deprecated embedded ESLint bridge.
    ignoreDuringBuilds: true,
  },
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
