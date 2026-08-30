/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  // Required for infrastructure/docker/Dockerfile.frontend, which copies
  // .next/standalone into the production image. Without this, the Docker
  // build succeeds up to `npm run build` but the COPY step for
  // .next/standalone fails because Next.js never produces that folder.
  output: 'standalone',
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
      {
        source: '/static/:path*',
        destination: 'http://127.0.0.1:8000/static/:path*',
      },
    ]
  },
}

module.exports = nextConfig
