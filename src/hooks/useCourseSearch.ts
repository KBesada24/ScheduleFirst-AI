import { useState, useEffect, useCallback, useRef } from "react";
import { searchCourses, CourseWithSections } from "@/lib/supabase-queries";
import { CourseFilters } from "@/components/ui/search-button";

interface SearchParams {
  query: string;
  filters: CourseFilters;
}

interface CacheEntry {
  data: CourseWithSections[];
  timestamp: number;
}

const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
const DEBOUNCE_DELAY = 300; // 300ms

export function useCourseSearch() {
  const [courses, setCourses] = useState<CourseWithSections[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [searchParams, setSearchParams] = useState<SearchParams>({
    query: "",
    filters: {},
  });

  // Cache for search results
  const cacheRef = useRef<Map<string, CacheEntry>>(new Map());
  
  // Debounce timer
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Generate cache key from search params
  const getCacheKey = useCallback((params: SearchParams): string => {
    return JSON.stringify({
      query: params.query.trim().toLowerCase(),
      filters: params.filters,
    });
  }, []);

  // Check if cache entry is valid
  const isCacheValid = useCallback((entry: CacheEntry): boolean => {
    return Date.now() - entry.timestamp < CACHE_DURATION;
  }, []);

  // Perform the actual search
  const performSearch = useCallback(async (params: SearchParams) => {
    const cacheKey = getCacheKey(params);
    
    // Check cache first
    const cachedEntry = cacheRef.current.get(cacheKey);
    if (cachedEntry && isCacheValid(cachedEntry)) {
      setCourses(cachedEntry.data);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const results = await searchCourses({
        query: params.query.trim() || undefined,
        department: params.filters.department !== "all" ? params.filters.department : undefined,
        semester: params.filters.semester || undefined,
        modality: params.filters.modality !== "all" ? params.filters.modality : undefined,
        timeSlot: params.filters.timeSlot !== "all" ? params.filters.timeSlot : undefined,
        limit: 50,
      });

      // Update cache
      cacheRef.current.set(cacheKey, {
        data: results,
        timestamp: Date.now(),
      });

      setCourses(results);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Search failed");
      setError(error);
      setCourses([]);
    } finally {
      setLoading(false);
    }
  }, [getCacheKey, isCacheValid]);

  // Debounced search effect
  useEffect(() => {
    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new timer
    debounceTimerRef.current = setTimeout(() => {
      if (searchParams.query || Object.keys(searchParams.filters).length > 0) {
        performSearch(searchParams);
      }
    }, DEBOUNCE_DELAY);

    // Cleanup
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [searchParams, performSearch]);

  // Update search parameters
  const search = useCallback((query: string, filters: CourseFilters) => {
    setSearchParams({ query, filters });
  }, []);

  // Clear search results
  const clear = useCallback(() => {
    setCourses([]);
    setError(null);
    setSearchParams({ query: "", filters: {} });
  }, []);

  // Clear cache
  const clearCache = useCallback(() => {
    cacheRef.current.clear();
  }, []);

  return {
    courses,
    loading,
    error,
    search,
    clear,
    clearCache,
  };
}
