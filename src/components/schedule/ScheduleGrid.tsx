import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle } from "lucide-react";
import { CourseSection } from "@/lib/supabase-queries";
import { useMemo, useRef, useEffect } from "react";

export interface ScheduleEvent {
  id: string;
  course_code: string;
  course_name: string;
  professor: string;
  location: string;
  days: string; // "MWF", "TTh", etc.
  start_time: string; // "10:00" or "10:00 AM"
  end_time: string; // "11:15" or "11:15 AM"
  color?: string;
}

export interface ScheduleGridProps {
  sections?: CourseSection[];
  events?: ScheduleEvent[];
  conflicts?: Array<{ section1: CourseSection; section2: CourseSection }>;
  onSectionClick?: (section: CourseSection | ScheduleEvent) => void;
  editable?: boolean;
}

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const DAY_ABBREV: Record<string, string> = {
  'M': 'Monday',
  'T': 'Tuesday',
  'W': 'Wednesday',
  'Th': 'Thursday',
  'F': 'Friday',
  'S': 'Saturday',
  'Su': 'Sunday'
};

const TIME_SLOTS = [
  '8:00', '9:00', '10:00', '11:00', '12:00',
  '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00'
];

const COLOR_PALETTE = [
  'bg-blue-500',
  'bg-purple-500',
  'bg-green-500',
  'bg-orange-500',
  'bg-pink-500',
  'bg-indigo-500',
  'bg-teal-500',
  'bg-red-500',
];

/**
 * ScheduleGrid - Enhanced calendar grid component for displaying course schedules
 * 
 * Features:
 * - Dynamic rendering based on sections or events
 * - Parses days (MWF, TTh, etc.) and maps to grid columns
 * - Calculates grid positions from start/end times
 * - Assigns distinct colors to each course
 * - Displays conflict indicators
 * - Supports click handlers for interactive editing
 * - Smooth transitions and animations
 * - Responsive design
 */
export default function ScheduleGrid({ 
  sections = [],
  events = [],
  conflicts = [],
  onSectionClick,
  editable = false
}: ScheduleGridProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const previousScrollTop = useRef<number>(0);

  // Maintain scroll position during updates
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = previousScrollTop.current;
    }
  }, [sections, events]);

  // Save scroll position before updates
  const handleScroll = () => {
    if (scrollContainerRef.current) {
      previousScrollTop.current = scrollContainerRef.current.scrollTop;
    }
  };
  
  /**
   * Convert time string to minutes since midnight
   * Handles both "10:00" and "10:00 AM" formats
   */
  const timeToMinutes = (time: string): number => {
    if (!time) return 0;
    
    // Remove any whitespace
    time = time.trim();
    
    // Check if time includes AM/PM
    const hasAMPM = time.includes('AM') || time.includes('PM');
    
    if (hasAMPM) {
      const [timePart, period] = time.split(' ');
      let [hours, minutes] = timePart.split(':').map(Number);
      
      if (period === 'PM' && hours !== 12) hours += 12;
      if (period === 'AM' && hours === 12) hours = 0;
      
      return hours * 60 + (minutes || 0);
    } else {
      // 24-hour format
      const [hours, minutes] = time.split(':').map(Number);
      return hours * 60 + (minutes || 0);
    }
  };

  /**
   * Format time for display (24-hour to 12-hour with AM/PM)
   */
  const formatTime = (time: string): string => {
    if (!time) return '';
    
    const minutes = timeToMinutes(time);
    let hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    const period = hours >= 12 ? 'PM' : 'AM';
    
    if (hours > 12) hours -= 12;
    if (hours === 0) hours = 12;
    
    return `${hours}:${mins.toString().padStart(2, '0')} ${period}`;
  };

  /**
   * Parse days string (e.g., "MWF", "TTh") into array of day names
   */
  const parseDays = (daysStr: string): string[] => {
    if (!daysStr) return [];
    
    const days: string[] = [];
    let i = 0;
    
    while (i < daysStr.length) {
      // Check for two-letter abbreviations first (Th, Su)
      if (i < daysStr.length - 1) {
        const twoChar = daysStr.substring(i, i + 2);
        if (DAY_ABBREV[twoChar]) {
          days.push(DAY_ABBREV[twoChar]);
          i += 2;
          continue;
        }
      }
      
      // Single letter abbreviation
      const oneChar = daysStr[i];
      if (DAY_ABBREV[oneChar]) {
        days.push(DAY_ABBREV[oneChar]);
      }
      i++;
    }
    
    return days;
  };

  /**
   * Calculate grid position for an event
   */
  const getEventPosition = (startTime: string, endTime: string) => {
    const startMinutes = timeToMinutes(startTime);
    const endMinutes = timeToMinutes(endTime);
    const baseMinutes = timeToMinutes('8:00');
    
    // Each hour is 80px
    const top = ((startMinutes - baseMinutes) / 60) * 80;
    const height = ((endMinutes - startMinutes) / 60) * 80;
    
    return { top, height };
  };

  /**
   * Get column index for a day
   */
  const getDayColumn = (day: string): number => {
    return DAYS.indexOf(day);
  };

  /**
   * Convert sections to events with proper formatting
   */
  const processedEvents = useMemo(() => {
    const allEvents: ScheduleEvent[] = [];
    const courseColors = new Map<string, string>();
    let colorIndex = 0;
    
    // Process sections from database
    sections.forEach((section) => {
      if (!section.days || !section.start_time || !section.end_time) return;
      
      // Assign color to course if not already assigned
      const courseKey = section.course_id || section.id;
      if (!courseColors.has(courseKey)) {
        courseColors.set(courseKey, COLOR_PALETTE[colorIndex % COLOR_PALETTE.length]);
        colorIndex++;
      }
      
      const days = parseDays(section.days);
      
      days.forEach((day) => {
        allEvents.push({
          id: `${section.id}-${day}`,
          course_code: section.section_number || 'N/A',
          course_name: section.section_number || 'Course',
          professor: section.professor_name || 'TBA',
          location: section.location || 'TBA',
          days: section.days,
          start_time: section.start_time,
          end_time: section.end_time,
          color: courseColors.get(courseKey),
        });
      });
    });
    
    // Add custom events
    events.forEach((event) => {
      if (!event.days || !event.start_time || !event.end_time) return;
      
      const days = parseDays(event.days);
      
      days.forEach((day) => {
        allEvents.push({
          ...event,
          id: `${event.id}-${day}`,
          color: event.color || COLOR_PALETTE[colorIndex % COLOR_PALETTE.length],
        });
      });
      
      colorIndex++;
    });
    
    return allEvents;
  }, [sections, events]);

  /**
   * Get events for a specific day
   */
  const getEventsForDay = (day: string) => {
    return processedEvents.filter((event) => {
      const eventDays = parseDays(event.days);
      return eventDays.includes(day);
    });
  };

  /**
   * Check if a section has conflicts
   */
  const hasConflict = (eventId: string): boolean => {
    return conflicts.some(
      (conflict) =>
        conflict.section1.id === eventId || conflict.section2.id === eventId
    );
  };

  /**
   * Get unique courses for legend
   */
  const uniqueCourses = useMemo(() => {
    const courseMap = new Map<string, ScheduleEvent>();
    
    processedEvents.forEach((event) => {
      const key = `${event.course_code}-${event.course_name}`;
      if (!courseMap.has(key)) {
        courseMap.set(key, event);
      }
    });
    
    return Array.from(courseMap.values());
  }, [processedEvents]);

  return (
    <Card className="w-full bg-white">
      <CardHeader>
        <CardTitle className="text-2xl font-bold text-gray-900">Weekly Schedule</CardTitle>
        {conflicts.length > 0 && (
          <div className="flex items-center gap-2 text-red-600 text-sm mt-2">
            <AlertCircle className="h-4 w-4" />
            <span>{conflicts.length} conflict{conflicts.length > 1 ? 's' : ''} detected</span>
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div 
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="overflow-x-auto"
        >
          <div className="min-w-[800px]">
            {/* Header with days */}
            <div className="grid grid-cols-6 gap-2 mb-2">
              <div className="text-sm font-semibold text-gray-600 p-2">Time</div>
              {DAYS.map((day) => (
                <div
                  key={day}
                  className="text-sm font-semibold text-gray-900 p-2 text-center bg-gray-50 rounded"
                >
                  {day}
                </div>
              ))}
            </div>

            {/* Time slots grid */}
            <div className="relative">
              {TIME_SLOTS.map((time, idx) => (
                <div
                  key={time}
                  className="grid grid-cols-6 gap-2 border-t border-gray-200"
                  style={{ height: '80px' }}
                >
                  <div className="text-xs text-gray-600 p-2">{formatTime(time)}</div>
                  {DAYS.map((day) => (
                    <div
                      key={`${day}-${time}`}
                      className="border-l border-gray-100 relative"
                    />
                  ))}
                </div>
              ))}

              {/* Render events */}
              {DAYS.map((day, dayIndex) => {
                const dayEvents = getEventsForDay(day);
                
                return dayEvents.map((event) => {
                  const { top, height } = getEventPosition(event.start_time, event.end_time);
                  const columnPercent = ((dayIndex + 1) / 6) * 100;
                  const widthPercent = (1 / 6) * 100;
                  const isConflict = hasConflict(event.id);
                  
                  return (
                    <div
                      key={event.id}
                      className={`absolute z-10 transition-all duration-300 ease-in-out animate-in fade-in slide-in-from-bottom-2 ${
                        editable ? 'cursor-pointer hover:shadow-lg hover:scale-105' : ''
                      }`}
                      style={{
                        top: `${top}px`,
                        left: `calc(${columnPercent}% + 0.5rem)`,
                        width: `calc(${widthPercent}% - 1rem)`,
                        height: `${height}px`,
                      }}
                      onClick={() => onSectionClick && onSectionClick(event)}
                    >
                      <div
                        className={`${event.color || 'bg-blue-500'} ${
                          isConflict ? 'ring-2 ring-red-500' : ''
                        } text-white p-2 rounded shadow-md h-full overflow-hidden`}
                      >
                        <div className="font-semibold text-sm truncate">{event.course_code}</div>
                        {height > 60 && (
                          <>
                            <div className="text-xs mt-1 truncate">{event.course_name}</div>
                            <div className="text-xs truncate">{event.professor}</div>
                          </>
                        )}
                        {height > 90 && (
                          <div className="text-xs truncate">{event.location}</div>
                        )}
                        {isConflict && (
                          <div className="absolute top-1 right-1">
                            <AlertCircle className="h-4 w-4 text-red-200" />
                          </div>
                        )}
                      </div>
                    </div>
                  );
                });
              })}
            </div>
          </div>
        </div>

        {/* Legend */}
        {uniqueCourses.length > 0 && (
          <div className="mt-4 flex gap-4 flex-wrap">
            {uniqueCourses.map((course) => (
              <div key={`${course.course_code}-${course.course_name}`} className="flex items-center gap-2">
                <div className={`w-4 h-4 ${course.color} rounded`}></div>
                <span className="text-sm text-gray-700">
                  {course.course_code} - {course.course_name}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {processedEvents.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg">No courses scheduled yet</p>
            <p className="text-sm mt-2">Add courses to see them on your schedule</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
