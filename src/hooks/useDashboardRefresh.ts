import { useState, useCallback, useRef } from "react";

export interface RefreshableData {
  key: string;
  refetch: () => Promise<void>;
}

export function useDashboardRefresh(refreshableItems: RefreshableData[] = []) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null);
  const scrollPositionRef = useRef<number>(0);

  /**
   * Save current scroll position
   */
  const saveScrollPosition = useCallback(() => {
    scrollPositionRef.current = window.scrollY;
  }, []);

  /**
   * Restore scroll position
   */
  const restoreScrollPosition = useCallback(() => {
    window.scrollTo(0, scrollPositionRef.current);
  }, []);

  /**
   * Refresh all dashboard data
   */
  const refreshAll = useCallback(async () => {
    if (isRefreshing) return;

    setIsRefreshing(true);
    saveScrollPosition();

    try {
      // Refresh all items in parallel
      await Promise.all(
        refreshableItems.map((item) => item.refetch())
      );

      setLastRefreshTime(new Date());
    } catch (error) {
      console.error("Error refreshing dashboard:", error);
      throw error;
    } finally {
      setIsRefreshing(false);
      
      // Restore scroll position after a brief delay to allow DOM updates
      setTimeout(restoreScrollPosition, 100);
    }
  }, [refreshableItems, isRefreshing, saveScrollPosition, restoreScrollPosition]);

  /**
   * Refresh a specific item
   */
  const refreshItem = useCallback(
    async (key: string) => {
      const item = refreshableItems.find((i) => i.key === key);
      if (!item) return;

      setIsRefreshing(true);
      saveScrollPosition();

      try {
        await item.refetch();
        setLastRefreshTime(new Date());
      } catch (error) {
        console.error(`Error refreshing ${key}:`, error);
        throw error;
      } finally {
        setIsRefreshing(false);
        setTimeout(restoreScrollPosition, 100);
      }
    },
    [refreshableItems, saveScrollPosition, restoreScrollPosition]
  );

  return {
    isRefreshing,
    lastRefreshTime,
    refreshAll,
    refreshItem,
  };
}
