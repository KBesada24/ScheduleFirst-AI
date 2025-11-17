import { useState, useCallback, useMemo } from "react";
import { CourseSection, checkScheduleConflicts } from "@/lib/supabase-queries";
import { ScheduleEvent } from "@/components/schedule/ScheduleGrid";

/**
 * useScheduleGrid - Hook for managing schedule grid state and updates
 * 
 * Features:
 * - Manages sections displayed on the grid
 * - Automatically detects conflicts
 * - Provides methods to add/remove sections
 * - Converts AI responses to grid format
 * - Handles smooth updates with transitions
 */
export function useScheduleGrid(initialSections: CourseSection[] = []) {
  const [sections, setSections] = useState<CourseSection[]>(initialSections);
  const [conflicts, setConflicts] = useState<Array<{ section1: CourseSection; section2: CourseSection }>>([]);
  const [isUpdating, setIsUpdating] = useState(false);

  /**
   * Check for conflicts whenever sections change
   */
  const updateConflicts = useCallback(async (newSections: CourseSection[]) => {
    if (newSections.length < 2) {
      setConflicts([]);
      return;
    }

    try {
      const sectionIds = newSections.map(s => s.id);
      const detectedConflicts = await checkScheduleConflicts(sectionIds);
      setConflicts(detectedConflicts.map(c => ({
        section1: c.section1,
        section2: c.section2
      })));
    } catch (error) {
      console.error("Error checking conflicts:", error);
      setConflicts([]);
    }
  }, []);

  /**
   * Add a section to the grid
   */
  const addSection = useCallback(async (section: CourseSection) => {
    setIsUpdating(true);
    
    // Check if section already exists
    if (sections.some(s => s.id === section.id)) {
      setIsUpdating(false);
      return;
    }

    const newSections = [...sections, section];
    setSections(newSections);
    await updateConflicts(newSections);
    
    // Delay to allow transition animation
    setTimeout(() => setIsUpdating(false), 300);
  }, [sections, updateConflicts]);

  /**
   * Remove a section from the grid
   */
  const removeSection = useCallback(async (sectionId: string) => {
    setIsUpdating(true);
    
    const newSections = sections.filter(s => s.id !== sectionId);
    setSections(newSections);
    await updateConflicts(newSections);
    
    setTimeout(() => setIsUpdating(false), 300);
  }, [sections, updateConflicts]);

  /**
   * Replace all sections (used for AI-generated schedules)
   */
  const setSectionsFromAI = useCallback(async (newSections: CourseSection[]) => {
    setIsUpdating(true);
    
    setSections(newSections);
    await updateConflicts(newSections);
    
    setTimeout(() => setIsUpdating(false), 300);
  }, [updateConflicts]);

  /**
   * Clear all sections
   */
  const clearSections = useCallback(() => {
    setIsUpdating(true);
    setSections([]);
    setConflicts([]);
    setTimeout(() => setIsUpdating(false), 300);
  }, []);

  /**
   * Convert AI response to sections format
   * Handles various AI response formats
   */
  const parseAISchedule = useCallback((aiResponse: any): CourseSection[] => {
    // Handle different AI response formats
    if (Array.isArray(aiResponse)) {
      return aiResponse;
    }

    if (aiResponse.sections) {
      return aiResponse.sections;
    }

    if (aiResponse.courses) {
      // Convert courses array to sections
      return aiResponse.courses.flatMap((course: any) => {
        if (course.sections) {
          return course.sections;
        }
        return [course];
      });
    }

    if (aiResponse.schedule) {
      return parseAISchedule(aiResponse.schedule);
    }

    return [];
  }, []);

  /**
   * Update grid from AI response
   */
  const updateFromAI = useCallback(async (aiResponse: any) => {
    const parsedSections = parseAISchedule(aiResponse);
    await setSectionsFromAI(parsedSections);
  }, [parseAISchedule, setSectionsFromAI]);

  /**
   * Convert sections to events format for ScheduleGrid
   */
  const events = useMemo((): ScheduleEvent[] => {
    return sections.map(section => ({
      id: section.id,
      course_code: section.section_number || 'N/A',
      course_name: section.section_number || 'Course',
      professor: section.professor_name || 'TBA',
      location: section.location || 'TBA',
      days: section.days || '',
      start_time: section.start_time || '',
      end_time: section.end_time || '',
    }));
  }, [sections]);

  return {
    sections,
    events,
    conflicts,
    isUpdating,
    addSection,
    removeSection,
    setSectionsFromAI,
    clearSections,
    updateFromAI,
    parseAISchedule,
  };
}
