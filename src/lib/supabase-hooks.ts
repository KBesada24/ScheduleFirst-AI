import { useState, useEffect } from "react";
import {
  searchCourses,
  getCourseById,
  searchProfessors,
  getProfessorById,
  getUserSchedules,
  getScheduleById,
  createSchedule,
  updateSchedule,
  addSectionToSchedule,
  removeSectionFromSchedule,
  deleteSchedule,
  checkScheduleConflicts,
  getOrCreateUserProfile,
  updateUserProfile,
  type CourseWithSections,
  type Professor,
  type ProfessorWithReviews,
  type UserSchedule,
  type ScheduleWithSections,
  type TimeConflict,
} from "./supabase-queries";
import { UserProfile } from "../types/user";

// ============================================
// COURSE HOOKS
// ============================================

export function useCourseSearch(params: {
  query?: string;
  department?: string;
  semester?: string;
  modality?: string;
  timeSlot?: string;
  university?: string;
  limit?: number;
}) {
  const [courses, setCourses] = useState<CourseWithSections[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const search = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await searchCourses(params);
      setCourses(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    search();
  }, [params.query, params.department, params.semester, params.modality, params.timeSlot, params.university]);

  return { courses, loading, error, refetch: search };
}

export function useCourse(courseId: string | null) {
  const [course, setCourse] = useState<CourseWithSections | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!courseId) return;

    const fetchCourse = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getCourseById(courseId);
        setCourse(data);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchCourse();
  }, [courseId]);

  return { course, loading, error };
}

// ============================================
// PROFESSOR HOOKS
// ============================================

export function useProfessorSearch(params: {
  query?: string;
  department?: string;
  university?: string;
  minRating?: number;
  limit?: number;
}) {
  const [professors, setProfessors] = useState<Professor[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const search = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await searchProfessors(params);
      setProfessors(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    search();
  }, [params.query, params.department, params.university, params.minRating]);

  return { professors, loading, error, refetch: search };
}

export function useProfessor(professorId: string | null) {
  const [professor, setProfessor] = useState<ProfessorWithReviews | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!professorId) return;

    const fetchProfessor = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getProfessorById(professorId);
        setProfessor(data);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchProfessor();
  }, [professorId]);

  return { professor, loading, error };
}

// ============================================
// SCHEDULE HOOKS
// ============================================

export function useUserSchedules(userId: string | null) {
  const [schedules, setSchedules] = useState<UserSchedule[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchSchedules = async () => {
    if (!userId) return;

    setLoading(true);
    setError(null);
    try {
      const data = await getUserSchedules(userId);
      setSchedules(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedules();
  }, [userId]);

  return { schedules, loading, error, refetch: fetchSchedules };
}

export function useSchedule(scheduleId: string | null) {
  const [schedule, setSchedule] = useState<ScheduleWithSections | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchSchedule = async () => {
    if (!scheduleId) return;

    setLoading(true);
    setError(null);
    try {
      const data = await getScheduleById(scheduleId);
      setSchedule(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule();
  }, [scheduleId]);

  return { schedule, loading, error, refetch: fetchSchedule };
}

export function useScheduleManager(scheduleId: string | null) {
  const { schedule, loading, error, refetch } = useSchedule(scheduleId);
  const [conflicts, setConflicts] = useState<TimeConflict[]>([]);
  const [actionLoading, setActionLoading] = useState(false);

  // Check for conflicts whenever schedule changes
  useEffect(() => {
    if (schedule?.sections) {
      checkScheduleConflicts(schedule.sections).then(setConflicts);
    }
  }, [schedule?.sections]);

  const addSection = async (sectionId: string) => {
    if (!scheduleId) throw new Error("No schedule ID");

    setActionLoading(true);
    try {
      await addSectionToSchedule(scheduleId, sectionId);
      await refetch();
    } finally {
      setActionLoading(false);
    }
  };

  const removeSection = async (sectionId: string) => {
    if (!scheduleId) throw new Error("No schedule ID");

    setActionLoading(true);
    try {
      await removeSectionFromSchedule(scheduleId, sectionId);
      await refetch();
    } finally {
      setActionLoading(false);
    }
  };

  const updateScheduleName = async (name: string) => {
    if (!scheduleId) throw new Error("No schedule ID");

    setActionLoading(true);
    try {
      await updateSchedule(scheduleId, { name });
      await refetch();
    } finally {
      setActionLoading(false);
    }
  };

  const deleteCurrentSchedule = async () => {
    if (!scheduleId) throw new Error("No schedule ID");

    setActionLoading(true);
    try {
      await deleteSchedule(scheduleId);
    } finally {
      setActionLoading(false);
    }
  };

  return {
    schedule,
    conflicts,
    loading,
    error,
    actionLoading,
    addSection,
    removeSection,
    updateScheduleName,
    deleteSchedule: deleteCurrentSchedule,
    refetch,
  };
}

export function useCreateSchedule() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const create = async (params: {
    user_id: string;
    semester: string;
    name: string;
    sections?: string[];
  }) => {
    setLoading(true);
    setError(null);
    try {
      const schedule = await createSchedule(params);
      return schedule;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { create, loading, error };
}

// ============================================
// USER HOOKS
// ============================================

export function useUserProfile(userId: string | null, email?: string) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchUser = async () => {
    if (!userId || !email) return;

    setLoading(true);
    setError(null);
    try {
      const data = await getOrCreateUserProfile(userId, email);
      setUser(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, [userId, email]);

  const updateProfile = async (updates: {
    name?: string;
    major?: string;
    graduation_year?: number;
    university?: string;
    preferences?: any;
  }) => {
    if (!userId) throw new Error("No user ID");

    setLoading(true);
    setError(null);
    try {
      const updated = await updateUserProfile(userId, updates);
      setUser(updated);
      return updated;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { user, loading, error, updateProfile, refetch: fetchUser };
}
