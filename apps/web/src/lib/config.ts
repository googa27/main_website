export const config = {
  API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  IS_DEV: process.env.NODE_ENV === 'development',
} as const;
