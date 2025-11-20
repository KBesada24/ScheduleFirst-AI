/**
 * Schedule Parser
 * 
 * Parse AI schedule suggestions into ScheduleGrid format
 */

import { CourseSection } from "./supabase-queries";

export interface AIScheduleSuggestion {
  sections?: CourseSection[];
  courses?: any[];
  schedule?: any;
  [key: string]: any;
}

/**
 * Validate schedule data structure
 */
export function validateScheduleData(data: any): boolean {
  if (!data) return false;

  // Check if it has sections array
  if (Array.isArray(data.sections)) {
    return data.sections.length > 0;
  }

  // Check if it has courses array
  if (Array.isArray(data.courses)) {
    return data.courses.length > 0;
  }

  // Check if it has schedule property
  if (data.schedule) {
    return validateScheduleData(data.schedule);
  }

  return false;
}

/**
 * Extract sections from various AI response formats
 */
export function extractSections(data: AIScheduleSuggestion): CourseSection[] {
  if (!data) return [];

  // Direct sections array
  if (Array.isArray(data.sections)) {
    return data.sections.filter(isValidSection);
  }

  // Courses array with sections
  if (Array.isArray(data.courses)) {
    const sections: CourseSection[] = [];
    
    data.courses.forEach((course) => {
      if (Array.isArray(course.sections)) {
        sections.push(...course.sections.filter(isValidSection));
      } else if (isValidSection(course)) {
        sections.push(course);
      }
    });
    
    return sections;
  }

  // Nested schedule property
  if (data.schedule) {
    return extractSections(data.schedule);
  }

  // Single section object
  if (isValidSection(data)) {
    return [data as CourseSection];
  }

  return [];
}

/**
 * Check if an object is a valid section
 */
function isValidSection(obj: any): obj is CourseSection {
  return (
    obj &&
    typeof obj === "object" &&
    typeof obj.id === "string" &&
    (typeof obj.days === "string" || obj.days === null) &&
    (typeof obj.start_time === "string" || obj.start_time === null) &&
    (typeof obj.end_time === "string" || obj.end_time === null)
  );
}

/**
 * Map AI schedule to ScheduleGrid format
 */
export function mapToScheduleGrid(data: AIScheduleSuggestion): CourseSection[] {
  const sections = extractSections(data);

  // Ensure all sections have required fields
  return sections.map((section) => ({
    id: section.id || `temp-${Date.now()}-${Math.random()}`,
    course_id: section.course_id || "",
    section_number: section.section_number || "N/A",
    professor_id: section.professor_id || null,
    professor_name: section.professor_name || "TBA",
    days: section.days || "",
    start_time: section.start_time || "",
    end_time: section.end_time || "",
    location: section.location || "TBA",
    modality: section.modality || "In-person",
    enrolled: section.enrolled || null,
    capacity: section.capacity || null,
    scraped_at: section.scraped_at || new Date().toISOString(),
    updated_at: section.updated_at || new Date().toISOString(),
  }));
}

/**
 * Parse days string and validate format
 */
export function parseDays(daysStr: string): string[] {
  if (!daysStr) return [];

  const validDays = ["M", "T", "W", "Th", "F", "S", "Su"];
  const days: string[] = [];
  let i = 0;

  while (i < daysStr.length) {
    // Check for two-letter abbreviations first (Th, Su)
    if (i < daysStr.length - 1) {
      const twoChar = daysStr.substring(i, i + 2);
      if (validDays.includes(twoChar)) {
        days.push(twoChar);
        i += 2;
        continue;
      }
    }

    // Single letter abbreviation
    const oneChar = daysStr[i];
    if (validDays.includes(oneChar)) {
      days.push(oneChar);
    }
    i++;
  }

  return days;
}

/**
 * Parse time string and validate format
 */
export function parseTime(timeStr: string): { hours: number; minutes: number } | null {
  if (!timeStr) return null;

  // Handle 24-hour format (e.g., "14:30")
  const time24Match = timeStr.match(/^(\d{1,2}):(\d{2})$/);
  if (time24Match) {
    return {
      hours: parseInt(time24Match[1], 10),
      minutes: parseInt(time24Match[2], 10),
    };
  }

  // Handle 12-hour format (e.g., "2:30 PM")
  const time12Match = timeStr.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
  if (time12Match) {
    let hours = parseInt(time12Match[1], 10);
    const minutes = parseInt(time12Match[2], 10);
    const period = time12Match[3].toUpperCase();

    if (period === "PM" && hours !== 12) {
      hours += 12;
    } else if (period === "AM" && hours === 12) {
      hours = 0;
    }

    return { hours, minutes };
  }

  return null;
}

/**
 * Calculate grid position for a time slot
 */
export function calculateGridPosition(
  startTime: string,
  endTime: string
): { row: number; span: number } | null {
  const start = parseTime(startTime);
  const end = parseTime(endTime);

  if (!start || !end) return null;

  // Assuming grid starts at 8:00 AM
  const baseHour = 8;
  const startMinutes = (start.hours - baseHour) * 60 + start.minutes;
  const endMinutes = (end.hours - baseHour) * 60 + end.minutes;

  // Each row represents 15 minutes
  const row = Math.floor(startMinutes / 15);
  const span = Math.ceil((endMinutes - startMinutes) / 15);

  return { row, span };
}

/**
 * Handle missing or invalid data gracefully
 */
export function sanitizeScheduleData(data: AIScheduleSuggestion): AIScheduleSuggestion {
  if (!data) {
    return { sections: [] };
  }

  const sections = extractSections(data);
  const sanitizedSections = sections.map((section) => ({
    ...section,
    days: section.days || "TBA",
    start_time: section.start_time || "TBA",
    end_time: section.end_time || "TBA",
    location: section.location || "TBA",
    professor_name: section.professor_name || "TBA",
    modality: section.modality || "In-person",
  }));

  return { sections: sanitizedSections };
}
