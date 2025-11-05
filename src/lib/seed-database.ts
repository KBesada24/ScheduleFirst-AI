import { supabase } from "../../supabase/supabase";

/**
 * Seed the database with sample data for testing
 * This creates courses, professors, sections, and reviews
 */
export async function seedDatabase() {
  console.log("🌱 Starting database seed...");

  try {
    // 1. Create sample professors
    const { data: professors, error: profError } = await supabase
      .from("professors")
      .insert([
        {
          name: "Dr. Sarah Johnson",
          university: "City College",
          department: "Computer Science",
          average_rating: 4.6,
          average_difficulty: 3.2,
          review_count: 47,
          grade_letter: "A",
          composite_score: 92,
          ratemyprof_id: "prof123",
        },
        {
          name: "Prof. Michael Chen",
          university: "City College",
          department: "Computer Science",
          average_rating: 4.2,
          average_difficulty: 3.8,
          review_count: 32,
          grade_letter: "B",
          composite_score: 85,
          ratemyprof_id: "prof124",
        },
        {
          name: "Dr. Emily Rodriguez",
          university: "Hunter College",
          department: "Mathematics",
          average_rating: 4.8,
          average_difficulty: 2.9,
          review_count: 68,
          grade_letter: "A",
          composite_score: 95,
          ratemyprof_id: "prof125",
        },
        {
          name: "Prof. David Kim",
          university: "City College",
          department: "Mathematics",
          average_rating: 3.9,
          average_difficulty: 4.1,
          review_count: 28,
          grade_letter: "C",
          composite_score: 78,
          ratemyprof_id: "prof126",
        },
      ])
      .select();

    if (profError) throw profError;
    console.log("✅ Created professors:", professors?.length);

    // 2. Create sample courses
    const { data: courses, error: courseError } = await supabase
      .from("courses")
      .insert([
        {
          course_code: "CSC 381",
          subject_code: "CSC",
          course_number: "381",
          name: "Introduction to Algorithms",
          description: "Study of fundamental algorithms and data structures",
          credits: 3,
          department: "Computer Science",
          university: "City College",
          semester: "Fall 2025",
        },
        {
          course_code: "CSC 220",
          subject_code: "CSC",
          course_number: "220",
          name: "Data Structures",
          description: "Advanced data structures and their applications",
          credits: 3,
          department: "Computer Science",
          university: "City College",
          semester: "Fall 2025",
        },
        {
          course_code: "MATH 301",
          subject_code: "MATH",
          course_number: "301",
          name: "Linear Algebra",
          description: "Vector spaces, matrices, and linear transformations",
          credits: 3,
          department: "Mathematics",
          university: "City College",
          semester: "Fall 2025",
        },
        {
          course_code: "MATH 201",
          subject_code: "MATH",
          course_number: "201",
          name: "Calculus II",
          description: "Integration techniques and series",
          credits: 4,
          department: "Mathematics",
          university: "Hunter College",
          semester: "Fall 2025",
        },
      ])
      .select();

    if (courseError) throw courseError;
    console.log("✅ Created courses:", courses?.length);

    // 3. Create course sections
    if (courses && professors) {
      const sections = [
        // CSC 381 sections
        {
          course_id: courses[0].id,
          section_number: "001",
          professor_id: professors[0].id,
          professor_name: professors[0].name,
          days: "MWF",
          start_time: "10:00:00",
          end_time: "11:15:00",
          location: "NAC 5/150",
          modality: "In-person",
          enrolled: 28,
          capacity: 35,
        },
        {
          course_id: courses[0].id,
          section_number: "002",
          professor_id: professors[1].id,
          professor_name: professors[1].name,
          days: "TTh",
          start_time: "14:30:00",
          end_time: "16:00:00",
          location: "NAC 6/113",
          modality: "Hybrid",
          enrolled: 32,
          capacity: 35,
        },
        // CSC 220 sections
        {
          course_id: courses[1].id,
          section_number: "001",
          professor_id: professors[0].id,
          professor_name: professors[0].name,
          days: "MW",
          start_time: "13:00:00",
          end_time: "14:30:00",
          location: "NAC 4/120",
          modality: "In-person",
          enrolled: 25,
          capacity: 30,
        },
        // MATH 301 sections
        {
          course_id: courses[2].id,
          section_number: "001",
          professor_id: professors[3].id,
          professor_name: professors[3].name,
          days: "TTh",
          start_time: "10:00:00",
          end_time: "11:30:00",
          location: "NAC 7/201",
          modality: "In-person",
          enrolled: 30,
          capacity: 35,
        },
        {
          course_id: courses[2].id,
          section_number: "002",
          professor_id: professors[3].id,
          professor_name: professors[3].name,
          days: "MWF",
          start_time: "15:00:00",
          end_time: "16:15:00",
          location: "NAC 7/202",
          modality: "In-person",
          enrolled: 28,
          capacity: 35,
        },
        // MATH 201 sections
        {
          course_id: courses[3].id,
          section_number: "001",
          professor_id: professors[2].id,
          professor_name: professors[2].name,
          days: "MWF",
          start_time: "09:00:00",
          end_time: "10:15:00",
          location: "Hunter North 401",
          modality: "In-person",
          enrolled: 35,
          capacity: 40,
        },
      ];

      const { data: sectionsData, error: sectionsError } = await supabase
        .from("course_sections")
        .insert(sections)
        .select();

      if (sectionsError) throw sectionsError;
      console.log("✅ Created sections:", sectionsData?.length);
    }

    // 4. Create sample reviews
    if (professors) {
      const reviews = [
        {
          professor_id: professors[0].id,
          review_text: "Amazing professor! Very clear explanations and helpful during office hours.",
          rating: 5.0,
          difficulty: 3.0,
          sentiment_positive: 95,
        },
        {
          professor_id: professors[0].id,
          review_text: "Great teacher but the exams are tough. Study hard!",
          rating: 4.5,
          difficulty: 3.5,
          sentiment_positive: 80,
        },
        {
          professor_id: professors[1].id,
          review_text: "Good professor but moves fast. Make sure to keep up with lectures.",
          rating: 4.0,
          difficulty: 4.0,
          sentiment_positive: 75,
        },
        {
          professor_id: professors[2].id,
          review_text: "Best math professor I've ever had! Makes complex topics easy to understand.",
          rating: 5.0,
          difficulty: 2.5,
          sentiment_positive: 98,
        },
      ];

      const { data: reviewsData, error: reviewsError } = await supabase
        .from("professor_reviews")
        .insert(reviews)
        .select();

      if (reviewsError) throw reviewsError;
      console.log("✅ Created reviews:", reviewsData?.length);
    }

    console.log("🎉 Database seeding completed successfully!");
    return { success: true };
  } catch (error) {
    console.error("❌ Error seeding database:", error);
    throw error;
  }
}

/**
 * Clear all data from the database (use with caution!)
 */
export async function clearDatabase() {
  console.log("🗑️  Clearing database...");

  try {
    // Delete in reverse order of dependencies
    await supabase.from("professor_reviews").delete().neq("id", "00000000-0000-0000-0000-000000000000");
    await supabase.from("user_schedules").delete().neq("id", "00000000-0000-0000-0000-000000000000");
    await supabase.from("course_sections").delete().neq("id", "00000000-0000-0000-0000-000000000000");
    await supabase.from("courses").delete().neq("id", "00000000-0000-0000-0000-000000000000");
    await supabase.from("professors").delete().neq("id", "00000000-0000-0000-0000-000000000000");

    console.log("✅ Database cleared successfully!");
    return { success: true };
  } catch (error) {
    console.error("❌ Error clearing database:", error);
    throw error;
  }
}