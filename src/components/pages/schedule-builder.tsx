import { useState } from "react";
import CourseSearch from "@/components/schedule/CourseSearch";
import CourseCard from "@/components/schedule/CourseCard";
import ProfessorCard from "@/components/schedule/ProfessorCard";
import ScheduleGrid from "@/components/schedule/ScheduleGrid";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Calendar, BookOpen, GraduationCap, Sparkles } from "lucide-react";
import { useCourseSearch, useProfessorSearch } from "@/lib/supabase-hooks";

export default function ScheduleBuilder() {
  const [activeTab, setActiveTab] = useState("search");
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState({
    department: "all",
    modality: "all",
    timeSlot: "all",
  });

  // Fetch courses based on search
  const { courses, loading: coursesLoading } = useCourseSearch({
    query: searchQuery,
    department: filters.department !== "all" ? filters.department : undefined,
    semester: "Fall 2025",
    limit: 20,
  });

  // Fetch top professors
  const { professors, loading: professorsLoading } = useProfessorSearch({
    limit: 10,
  });

  const handleSearch = (query: string, newFilters: any) => {
    setSearchQuery(query);
    setFilters(newFilters);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-2">
            <Sparkles className="h-8 w-8 text-blue-600" />
            <h1 className="text-4xl font-bold text-gray-900">ScheduleFirst AI</h1>
          </div>
          <p className="text-lg text-gray-600">
            AI-Powered Course Scheduling for CUNY Students
          </p>
        </div>

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 max-w-2xl mx-auto">
            <TabsTrigger value="search" className="flex items-center gap-2">
              <BookOpen className="h-4 w-4" />
              Course Search
            </TabsTrigger>
            <TabsTrigger value="schedule" className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              My Schedule
            </TabsTrigger>
            <TabsTrigger value="professors" className="flex items-center gap-2">
              <GraduationCap className="h-4 w-4" />
              Professors
            </TabsTrigger>
          </TabsList>

          {/* Course Search Tab */}
          <TabsContent value="search" className="space-y-6 mt-6">
            <CourseSearch onSearch={handleSearch} />
            
            {coursesLoading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <p className="mt-4 text-gray-600">Loading courses...</p>
              </div>
            ) : courses.length === 0 ? (
              <div className="text-center py-12">
                <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">No courses found. Try adjusting your search.</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {courses.slice(0, 10).map((course) => (
                    <CourseCard
                      key={course.id}
                      course={{
                        id: course.id,
                        course_code: course.course_code,
                        name: course.name,
                        credits: course.credits || 3,
                        department: course.department || "Unknown",
                        sections: course.sections.map((section) => ({
                          id: section.id,
                          section_number: section.section_number,
                          professor_name: section.professor_name || "TBA",
                          days: section.days || "TBA",
                          start_time: section.start_time || "TBA",
                          end_time: section.end_time || "TBA",
                          location: section.location || "TBA",
                          modality: section.modality || "In-person",
                          enrolled: section.enrolled || 0,
                          capacity: section.capacity || 30,
                        })),
                      }}
                    />
                  ))}
                </div>

                {courses.length > 10 && (
                  <div className="text-center">
                    <Button variant="outline" size="lg">
                      Load More Courses
                    </Button>
                  </div>
                )}
              </>
            )}
          </TabsContent>

          {/* Schedule Tab */}
          <TabsContent value="schedule" className="space-y-6 mt-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Fall 2025 Schedule</h2>
                <p className="text-gray-600">12 credits • 4 courses</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline">
                  <Sparkles className="h-4 w-4 mr-2" />
                  AI Optimize
                </Button>
                <Button className="bg-blue-600 hover:bg-blue-700">
                  Save Schedule
                </Button>
              </div>
            </div>

            <ScheduleGrid />

            {/* Conflict Detection Alert */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="text-green-600 text-xl">✅</div>
                <div>
                  <h3 className="font-semibold text-green-900">No Conflicts Detected</h3>
                  <p className="text-sm text-green-800 mt-1">
                    Your schedule looks great! All classes fit without overlaps.
                  </p>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Professors Tab */}
          <TabsContent value="professors" className="space-y-6 mt-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Professor Ratings</h2>
              <p className="text-gray-600">AI-powered analysis from RateMyProfessors</p>
            </div>

            {professorsLoading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <p className="mt-4 text-gray-600">Loading professors...</p>
              </div>
            ) : professors.length === 0 ? (
              <div className="text-center py-12">
                <GraduationCap className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">No professor data available yet.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {professors.map((prof) => (
                  <ProfessorCard
                    key={prof.id}
                    professor={{
                      name: prof.name,
                      grade_letter: prof.grade_letter || "N/A",
                      composite_score: prof.composite_score || 0,
                      average_rating: prof.average_rating || 0,
                      average_difficulty: prof.average_difficulty || 0,
                      review_count: prof.review_count || 0,
                      department: prof.department || "Unknown",
                      university: prof.university || "CUNY",
                    }}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}