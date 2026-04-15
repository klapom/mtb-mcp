"use client";

import useSWR from "swr";
import { api } from "@/lib/api";

const CACHE_PREFIX = "trailpilot_cache_";

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

function getCache<T>(key: string, ttlMs: number): T | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const raw = localStorage.getItem(CACHE_PREFIX + key);
    if (!raw) return undefined;
    const entry: CacheEntry<T> = JSON.parse(raw);
    if (Date.now() - entry.timestamp > ttlMs) {
      localStorage.removeItem(CACHE_PREFIX + key);
      return undefined;
    }
    return entry.data;
  } catch {
    return undefined;
  }
}

function setCache<T>(key: string, data: T): void {
  if (typeof window === "undefined") return;
  try {
    const entry: CacheEntry<T> = { data, timestamp: Date.now() };
    localStorage.setItem(CACHE_PREFIX + key, JSON.stringify(entry));
  } catch {
    // localStorage full — silently ignore
  }
}

/**
 * Like useApi but with localStorage caching + offline fallback.
 * @param path API path (or null to skip)
 * @param ttlMs Cache TTL in milliseconds (default: 1 hour)
 */
export function useCachedApi<T>(path: string | null, ttlMs = 60 * 60 * 1000) {
  const cacheKey = path ?? "";

  const result = useSWR<T>(
    path,
    async (url: string) => {
      try {
        const data = await api<T>(url);
        // Cache successful response
        setCache(cacheKey, data);
        return data;
      } catch (err) {
        // On network error, try returning cached data
        const cached = getCache<T>(cacheKey, ttlMs * 10); // Allow stale cache on error
        if (cached !== undefined) return cached;
        throw err;
      }
    },
    {
      revalidateOnFocus: false,
      errorRetryCount: 1,
      // Use cached data as initial fallback
      fallbackData: path ? getCache<T>(cacheKey, ttlMs) : undefined,
    },
  );

  return {
    ...result,
    isFromCache: result.data !== undefined && result.isLoading,
  };
}
