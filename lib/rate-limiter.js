const WINDOW_MS = 60 * 1000;
const LIMIT = 10;
const buckets = new Map();

export function rateLimit(key, options = {}) {
  const limit = options.limit ?? LIMIT;
  const windowMs = options.windowMs ?? WINDOW_MS;
  const now = Date.now();
  const bucket = buckets.get(key) || [];
  const windowStart = now - windowMs;

  const recent = bucket.filter((timestamp) => timestamp > windowStart);
  recent.push(now);
  buckets.set(key, recent);

  const remaining = Math.max(0, limit - recent.length);
  return {
    allowed: recent.length <= limit,
    remaining,
    resetMs: windowMs
  };
}
