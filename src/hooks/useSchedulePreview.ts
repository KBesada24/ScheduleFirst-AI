import { useState, useCallback } from "react";
import { CourseSection } from "@/lib/supabase-queries";

export interface ScheduleOption {
  id: string;
  sections: CourseSection[];
  score?: number;
  reasoning?: string;
  metadata?: {
    avgProfessorRating?: number;
    totalCredits?: number;
    daysPerWeek?: number;
    gapHours?: number;
  };
}

export function useSchedulePreview() {
  const [scheduleOptions, setScheduleOptions] = useState<ScheduleOption[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [isPreviewMode, setIsPreviewMode] = useState(false);

  /**
   * Set multiple schedule options for preview
   */
  const setOptions = useCallback((options: ScheduleOption[]) => {
    setScheduleOptions(options);
    setSelectedIndex(0);
    setIsPreviewMode(options.length > 0);
  }, []);

  /**
   * Get currently selected schedule
   */
  const selectedSchedule = scheduleOptions[selectedIndex] || null;

  /**
   * Switch to a different schedule option
   */
  const selectSchedule = useCallback(
    (index: number) => {
      if (index >= 0 && index < scheduleOptions.length) {
        setSelectedIndex(index);
      }
    },
    [scheduleOptions.length]
  );

  /**
   * Go to next schedule option
   */
  const nextSchedule = useCallback(() => {
    setSelectedIndex((prev) => 
      prev < scheduleOptions.length - 1 ? prev + 1 : prev
    );
  }, [scheduleOptions.length]);

  /**
   * Go to previous schedule option
   */
  const previousSchedule = useCallback(() => {
    setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev));
  }, []);

  /**
   * Clear all schedule options
   */
  const clearOptions = useCallback(() => {
    setScheduleOptions([]);
    setSelectedIndex(0);
    setIsPreviewMode(false);
  }, []);

  /**
   * Exit preview mode
   */
  const exitPreview = useCallback(() => {
    setIsPreviewMode(false);
  }, []);

  /**
   * Enter preview mode
   */
  const enterPreview = useCallback(() => {
    if (scheduleOptions.length > 0) {
      setIsPreviewMode(true);
    }
  }, [scheduleOptions.length]);

  return {
    scheduleOptions,
    selectedSchedule,
    selectedIndex,
    isPreviewMode,
    setOptions,
    selectSchedule,
    nextSchedule,
    previousSchedule,
    clearOptions,
    exitPreview,
    enterPreview,
  };
}
