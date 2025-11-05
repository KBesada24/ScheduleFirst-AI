import { supabase } from "../../supabase/supabase";

// ============================================
// COURSE QUERIES
// ============================================

export interface Course {
  id: string;
  course_code: string;
  subject_code: string | null;
  course_number: string | null;
  name: string;
  description: string | null;
  credits: number | null;
  department: string | null;
  university: string | null;
  semester: string;
  last_scraped: string;
  created_at: string;
}

export interface CourseSection {
  id: string;
  course_id: string;
  section_number: string;
  professor_id: string | null;
  professor_name: string | null;
  days: string | null;
  start_time: string | null;
  end_time: string | null;
  location: string | null;
  modality: string | null;
  enrolled: number | null;
  capacity: number | null;
  scraped_at: string;
  updated_at: string;
}

export interface CourseWithSections extends Course {
  sections: CourseSection[];
}

// Search courses with filters
export async function searchCourses(params: {
  query?: string;
  department?: string;
  semester?: string;
  modality?: string;
  timeSlot?: string;
  limit?: number;
  offset?: number;
}) {
  let query = supabase
    .from("courses")
    .select(`
      *,
      sections:course_sections(*)
    `)
    .order("course_code", { ascending: true });

  if (params.query) {
    query = query.or(`course_code.ilike.%${params.query}%,name.ilike.%${params.query}%,department.ilike.%${params.query}%`);
  }

  if (params.department && params.department !== "all") {
    query = query.ilike("department", `%${params.department}%`);
  }

  if (params.semester) {
    query = query.eq("semester", params.semester);
  }

  if (params.limit) {
    query = query.limit(params.limit);
  }

  if (params.offset) {
    query = query.range(params.offset, params.offset + (params.limit || 10) - 1);
  }

  const { data, error } = await query;

  if (error) throw error;
  return data as CourseWithSections[];
}

// Get course by ID with sections
export async function getCourseById(courseId: string) {
  const { data, error } = await supabase
    .from("courses")
    .select(`
      *,
      sections:course_sections(*)
    `)
    .eq("id", courseId)
    .single();

  if (error) throw error;
  return data as CourseWithSections;
}

// Get course by code
export async function getCourseByCode(courseCode: string, semester: string) {
  const { data, error } = await supabase
    .from("courses")
    .select(`
      *,
      sections:course_sections(*)
    `)
    .eq("course_code", courseCode)
    .eq("semester", semester)
    .single();

  if (error) throw error;
  return data as CourseWithSections;
}

// ============================================
// PROFESSOR QUERIES
// ============================================

export interface Professor {
  id: string;
  name: string;
  ratemyprof_id: string | null;
  university: string | null;
  department: string | null;
  average_rating: number | null;
  average_difficulty: number | null;
  review_count: number | null;
  grade_letter: string | null;
  composite_score: number | null;
  last_updated: string | null;
  created_at: string;
}

export interface ProfessorReview {
  id: string;
  professor_id: string;
  review_text: string | null;
  rating: number | null;
  difficulty: number | null;
  sentiment_positive: number | null;
  sentiment_aspects: any;
  created_at: string;
  scraped_at: string | null;
}

export interface ProfessorWithReviews extends Professor {
  reviews: ProfessorReview[];
}

// Get professor by ID with reviews
export async function getProfessorById(professorId: string) {
  const { data, error } = await supabase
    .from("professors")
    .select(`
      *,
      reviews:professor_reviews(*)
    `)
    .eq("id", professorId)
    .single();

  if (error) throw error;
  return data as ProfessorWithReviews;
}

// Get professor by name
export async function getProfessorByName(name: string, university?: string) {
  let query = supabase
    .from("professors")
    .select(`
      *,
      reviews:professor_reviews(*)
    `)
    .ilike("name", `%${name}%`);

  if (university) {
    query = query.eq("university", university);
  }

  const { data, error } = await query;

  if (error) throw error;
  return data as ProfessorWithReviews[];
}

// Search professors with filters
export async function searchProfessors(params: {
  query?: string;
  department?: string;
  university?: string;
  minRating?: number;
  limit?: number;
}) {
  let query = supabase
    .from("professors")
    .select("*")
    .order("composite_score", { ascending: false, nullsFirst: false });

  if (params.query) {
    query = query.ilike("name", `%${params.query}%`);
  }

  if (params.department) {
    query = query.eq("department", params.department);
  }

  if (params.university) {
    query = query.eq("university", params.university);
  }

  if (params.minRating) {
    query = query.gte("average_rating", params.minRating);
  }

  if (params.limit) {
    query = query.limit(params.limit);
  }

  const { data, error } = await query;

  if (error) throw error;
  return data as Professor[];
}

// Get top-rated professors
export async function getTopProfessors(limit: number = 10) {
  const { data, error } = await supabase
    .from("professors")
    .select("*")
    .not("composite_score", "is", null)
    .order("composite_score", { ascending: false })
    .limit(limit);

  if (error) throw error;
  return data as Professor[];
}

// ============================================
// SCHEDULE QUERIES
// ============================================

export interface UserSchedule {
  id: string;
  user_id: string;
  semester: string | null;
  name: string;
  sections: string[];
  created_at: string;
  updated_at: string;
}

export interface ScheduleWithSections extends UserSchedule {
  section_details: CourseSection[];
}

// Get user schedules
export async function getUserSchedules(userId: string) {
  const { data, error } = await supabase
    .from("user_schedules")
    .select("*")
    .eq("user_id", userId)
    .order("updated_at", { ascending: false });

  if (error) throw error;
  return data as UserSchedule[];
}

// Get schedule by ID with section details
export async function getScheduleById(scheduleId: string) {
  const { data: schedule, error: scheduleError } = await supabase
    .from("user_schedules")
    .select("*")
    .eq("id", scheduleId)
    .single();

  if (scheduleError) throw scheduleError;

  if (schedule.sections && schedule.sections.length > 0) {
    const { data: sections, error: sectionsError } = await supabase
      .from("course_sections")
      .select("*")
      .in("id", schedule.sections);

    if (sectionsError) throw sectionsError;

    return {
      ...schedule,
      section_details: sections,
    } as ScheduleWithSections;
  }

  return {
    ...schedule,
    section_details: [],
  } as ScheduleWithSections;
}

// Create new schedule
export async function createSchedule(params: {
  user_id: string;
  semester: string;
  name: string;
  sections?: string[];
}) {
  const { data, error } = await supabase
    .from("user_schedules")
    .insert({
      user_id: params.user_id,
      semester: params.semester,
      name: params.name,
      sections: params.sections || [],
    })
    .select()
    .single();

  if (error) throw error;
  return data as UserSchedule;
}

// Update schedule
export async function updateSchedule(
  scheduleId: string,
  updates: {
    name?: string;
    sections?: string[];
    semester?: string;
  }
) {
  const { data, error } = await supabase
    .from("user_schedules")
    .update({
      ...updates,
      updated_at: new Date().toISOString(),
    })
    .eq("id", scheduleId)
    .select()
    .single();

  if (error) throw error;
  return data as UserSchedule;
}

// Add section to schedule
export async function addSectionToSchedule(scheduleId: string, sectionId: string) {
  const { data: schedule, error: fetchError } = await supabase
    .from("user_schedules")
    .select("sections")
    .eq("id", scheduleId)
    .single();

  if (fetchError) throw fetchError;

  const currentSections = schedule.sections || [];
  if (currentSections.includes(sectionId)) {
    throw new Error("Section already in schedule");
  }

  const { data, error } = await supabase
    .from("user_schedules")
    .update({
      sections: [...currentSections, sectionId],
      updated_at: new Date().toISOString(),
    })
    .eq("id", scheduleId)
    .select()
    .single();

  if (error) throw error;
  return data as UserSchedule;
}

// Remove section from schedule
export async function removeSectionFromSchedule(scheduleId: string, sectionId: string) {
  const { data: schedule, error: fetchError } = await supabase
    .from("user_schedules")
    .select("sections")
    .eq("id", scheduleId)
    .single();

  if (fetchError) throw fetchError;

  const currentSections = schedule.sections || [];
  const updatedSections = currentSections.filter((id) => id !== sectionId);

  const { data, error } = await supabase
    .from("user_schedules")
    .update({
      sections: updatedSections,
      updated_at: new Date().toISOString(),
    })
    .eq("id", scheduleId)
    .select()
    .single();

  if (error) throw error;
  return data as UserSchedule;
}

// Delete schedule
export async function deleteSchedule(scheduleId: string) {
  const { error } = await supabase
    .from("user_schedules")
    .delete()
    .eq("id", scheduleId);

  if (error) throw error;
}

// ============================================
// SECTION QUERIES
// ============================================

// Get section by ID
export async function getSectionById(sectionId: string) {
  const { data, error } = await supabase
    .from("course_sections")
    .select(`
      *,
      course:courses(*),
      professor:professors(*)
    `)
    .eq("id", sectionId)
    .single();

  if (error) throw error;
  return data;
}

// Get sections by course ID
export async function getSectionsByCourseId(courseId: string) {
  const { data, error } = await supabase
    .from("course_sections")
    .select("*")
    .eq("course_id", courseId)
    .order("section_number", { ascending: true });

  if (error) throw error;
  return data as CourseSection[];
}

// Get sections by professor ID
export async function getSectionsByProfessorId(professorId: string) {
  const { data, error } = await supabase
    .from("course_sections")
    .select(`
      *,
      course:courses(*)
    `)
    .eq("professor_id", professorId);

  if (error) throw error;
  return data;
}

// ============================================
// CONFLICT DETECTION
// ============================================

export interface TimeConflict {
  section1: CourseSection;
  section2: CourseSection;
  conflictType: "time" | "full";
}

// Check for schedule conflicts
export async function checkScheduleConflicts(sectionIds: string[]): Promise<TimeConflict[]> {
  if (sectionIds.length === 0) return [];

  const { data: sections, error } = await supabase
    .from("course_sections")
    .select("*")
    .in("id", sectionIds);

  if (error) throw error;

  const conflicts: TimeConflict[] = [];

  for (let i = 0; i < sections.length; i++) {
    for (let j = i + 1; j < sections.length; j++) {
      const s1 = sections[i];
      const s2 = sections[j];

      // Check if days overlap
      if (s1.days && s2.days) {
        const days1 = s1.days.split("");
        const days2 = s2.days.split("");
        const hasCommonDay = days1.some((day) => days2.includes(day));

        if (hasCommonDay && s1.start_time && s1.end_time && s2.start_time && s2.end_time) {
          // Check if times overlap
          const start1 = s1.start_time;
          const end1 = s1.end_time;
          const start2 = s2.start_time;
          const end2 = s2.end_time;

          if (
            (start1 < end2 && end1 > start2) ||
            (start2 < end1 && end2 > start1)
          ) {
            conflicts.push({
              section1: s1,
              section2: s2,
              conflictType: "time",
            });
          }
        }
      }
    }
  }

  return conflicts;
}

// ============================================
// USER QUERIES
// ============================================

export interface User {
  id: string;
  email: string;
  name: string | null;
  major: string | null;
  graduation_year: number | null;
  preferences: any;
  created_at: string;
  updated_at: string;
}

// Get or create user profile
export async function getOrCreateUserProfile(userId: string, email: string) {
  const { data: existing, error: fetchError } = await supabase
    .from("users")
    .select("*")
    .eq("id", userId)
    .single();

  if (existing) return existing as User;

  const { data, error } = await supabase
    .from("users")
    .insert({
      id: userId,
      email: email,
    })
    .select()
    .single();

  if (error) throw error;
  return data as User;
}

// Update user profile
export async function updateUserProfile(
  userId: string,
  updates: {
    name?: string;
    major?: string;
    graduation_year?: number;
    preferences?: any;
  }
) {
  const { data, error } = await supabase
    .from("users")
    .update({
      ...updates,
      updated_at: new Date().toISOString(),
    })
    .eq("id", userId)
    .select()
    .single();

  if (error) throw error;
  return data as User;
}

// ============================================
// ANALYTICS & STATS
// ============================================

// Get course enrollment stats
export async function getCourseEnrollmentStats(courseId: string) {
  const { data, error } = await supabase
    .from("course_sections")
    .select("enrolled, capacity")
    .eq("course_id", courseId);

  if (error) throw error;

  const totalEnrolled = data.reduce((sum, s) => sum + (s.enrolled || 0), 0);
  const totalCapacity = data.reduce((sum, s) => sum + (s.capacity || 0), 0);
  const availableSeats = totalCapacity - totalEnrolled;
  const fillRate = totalCapacity > 0 ? (totalEnrolled / totalCapacity) * 100 : 0;

  return {
    totalEnrolled,
    totalCapacity,
    availableSeats,
    fillRate,
    sectionCount: data.length,
  };
}

// Get professor teaching load
export async function getProfessorTeachingLoad(professorId: string, semester: string) {
  const { data, error } = await supabase
    .from("course_sections")
    .select(`
      *,
      course:courses(*)
    `)
    .eq("professor_id", professorId)
    .eq("course.semester", semester);

  if (error) throw error;
  return data;
}