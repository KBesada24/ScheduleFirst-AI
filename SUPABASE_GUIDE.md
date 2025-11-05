# ScheduleFirst AI - Supabase Integration Guide

## 🗄️ Database Connection

The app is fully connected to Supabase with comprehensive query functions and React hooks.

## 📁 File Structure

```
src/
├── lib/
│   ├── supabase-queries.ts    # All database query functions
│   ├── supabase-hooks.ts      # React hooks for queries
│   └── seed-database.ts       # Database seeding utilities
├── supabase/
│   └── supabase.ts            # Supabase client configuration
```

## 🔧 Available Query Functions

### Course Queries

```typescript
import { searchCourses, getCourseById, getCourseByCode } from "@/lib/supabase-queries";

// Search courses with filters
const courses = await searchCourses({
  query: "algorithms",
  department: "Computer Science",
  semester: "Fall 2025",
  modality: "in-person",
  limit: 20,
});

// Get specific course with sections
const course = await getCourseById("course-uuid");
const course = await getCourseByCode("CSC 381", "Fall 2025");
```

### Professor Queries

```typescript
import { 
  getProfessorById, 
  getProfessorByName, 
  searchProfessors,
  getTopProfessors 
} from "@/lib/supabase-queries";

// Search professors
const professors = await searchProfessors({
  query: "Johnson",
  department: "Computer Science",
  minRating: 4.0,
  limit: 10,
});

// Get top-rated professors
const topProfs = await getTopProfessors(10);

// Get professor with reviews
const prof = await getProfessorById("prof-uuid");
```

### Schedule Queries

```typescript
import {
  getUserSchedules,
  getScheduleById,
  createSchedule,
  updateSchedule,
  addSectionToSchedule,
  removeSectionFromSchedule,
  deleteSchedule,
  checkScheduleConflicts,
} from "@/lib/supabase-queries";

// Get user's schedules
const schedules = await getUserSchedules("user-uuid");

// Create new schedule
const schedule = await createSchedule({
  user_id: "user-uuid",
  semester: "Fall 2025",
  name: "My Schedule",
  sections: [],
});

// Add section to schedule
await addSectionToSchedule("schedule-uuid", "section-uuid");

// Check for conflicts
const conflicts = await checkScheduleConflicts(["section1-uuid", "section2-uuid"]);
```

### Section Queries

```typescript
import {
  getSectionById,
  getSectionsByCourseId,
  getSectionsByProfessorId,
} from "@/lib/supabase-queries";

// Get section details
const section = await getSectionById("section-uuid");

// Get all sections for a course
const sections = await getSectionsByCourseId("course-uuid");
```

### User Queries

```typescript
import { getOrCreateUserProfile, updateUserProfile } from "@/lib/supabase-queries";

// Get or create user profile
const user = await getOrCreateUserProfile("user-uuid", "email@example.com");

// Update profile
await updateUserProfile("user-uuid", {
  name: "John Doe",
  major: "Computer Science",
  graduation_year: 2026,
});
```

## 🪝 React Hooks

### Course Hooks

```typescript
import { useCourseSearch, useCourse } from "@/lib/supabase-hooks";

function MyComponent() {
  // Search courses with auto-refetch on param changes
  const { courses, loading, error, refetch } = useCourseSearch({
    query: "algorithms",
    department: "Computer Science",
    semester: "Fall 2025",
  });

  // Get single course
  const { course, loading, error } = useCourse("course-uuid");

  return <div>{/* Use courses data */}</div>;
}
```

### Professor Hooks

```typescript
import { useProfessorSearch, useProfessor } from "@/lib/supabase-hooks";

function ProfessorList() {
  const { professors, loading, error } = useProfessorSearch({
    department: "Computer Science",
    minRating: 4.0,
  });

  return <div>{/* Render professors */}</div>;
}
```

### Schedule Hooks

```typescript
import { 
  useUserSchedules, 
  useSchedule, 
  useScheduleManager,
  useCreateSchedule 
} from "@/lib/supabase-hooks";

function ScheduleManager() {
  // Get all user schedules
  const { schedules, loading } = useUserSchedules("user-uuid");

  // Manage a specific schedule
  const {
    schedule,
    conflicts,
    addSection,
    removeSection,
    updateScheduleName,
    deleteSchedule,
  } = useScheduleManager("schedule-uuid");

  // Create new schedule
  const { create, loading: creating } = useCreateSchedule();

  const handleCreate = async () => {
    const newSchedule = await create({
      user_id: "user-uuid",
      semester: "Fall 2025",
      name: "My New Schedule",
    });
  };

  return <div>{/* Schedule UI */}</div>;
}
```

### User Profile Hook

```typescript
import { useUserProfile } from "@/lib/supabase-hooks";

function ProfilePage() {
  const { user, loading, updateProfile } = useUserProfile("user-uuid", "email@example.com");

  const handleUpdate = async () => {
    await updateProfile({
      name: "Jane Doe",
      major: "Mathematics",
    });
  };

  return <div>{/* Profile UI */}</div>;
}
```

## 🌱 Database Seeding

### Seed Sample Data

```typescript
import { seedDatabase, clearDatabase } from "@/lib/seed-database";

// Seed database with sample data
await seedDatabase();

// Clear all data (use with caution!)
await clearDatabase();
```

Or use the Admin page at `/admin` to seed/clear via UI.

## 📊 Database Schema

### Tables

- **users** - Student profiles and preferences
- **courses** - Course catalog
- **course_sections** - Section details (time, location, professor)
- **professors** - Professor profiles with AI ratings
- **professor_reviews** - Scraped reviews with sentiment
- **user_schedules** - Saved student schedules

### Key Features

- ✅ Real-time subscriptions enabled
- ✅ Automatic timestamps
- ✅ Foreign key relationships
- ✅ Indexed for performance
- ✅ RLS disabled by default (enable as needed)

## 🚀 Usage Examples

### Complete Schedule Builder Flow

```typescript
import { useCourseSearch, useScheduleManager } from "@/lib/supabase-hooks";

function ScheduleBuilder() {
  const { courses } = useCourseSearch({ semester: "Fall 2025" });
  const { schedule, conflicts, addSection } = useScheduleManager("schedule-uuid");

  const handleAddCourse = async (sectionId: string) => {
    await addSection(sectionId);
    // Conflicts are automatically checked
    if (conflicts.length > 0) {
      alert("Schedule conflict detected!");
    }
  };

  return (
    <div>
      {courses.map((course) => (
        <CourseCard
          key={course.id}
          course={course}
          onAddSection={handleAddCourse}
        />
      ))}
    </div>
  );
}
```

### Professor Rating Display

```typescript
import { useProfessor } from "@/lib/supabase-hooks";

function ProfessorDetail({ professorId }: { professorId: string }) {
  const { professor, loading } = useProfessor(professorId);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1>{professor?.name}</h1>
      <div>Grade: {professor?.grade_letter}</div>
      <div>Score: {professor?.composite_score}</div>
      <div>Rating: {professor?.average_rating}/5.0</div>
      <div>Reviews: {professor?.review_count}</div>
    </div>
  );
}
```

## 🔐 Environment Variables

Required environment variables (already configured):

```
VITE_SUPABASE_URL=your-project-url
VITE_SUPABASE_ANON_KEY=your-anon-key
```

## 📝 Notes

- All queries include proper error handling
- Hooks automatically refetch on dependency changes
- Conflict detection runs automatically when schedule changes
- Database seeding creates realistic test data
- All timestamps are in ISO format

## 🎯 Next Steps

1. **Seed the database**: Visit `/admin` and click "Seed Database"
2. **Test queries**: Use the Schedule Builder to see live data
3. **Add authentication**: Connect Supabase Auth for user management
4. **Build MCP server**: Create Python backend for AI features
5. **Integrate Gemini**: Add AI recommendations

---

**All database queries are ready to use! 🎉**
