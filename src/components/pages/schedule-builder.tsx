import { useState } from "react";
import CourseSearch from "@/components/schedule/CourseSearch";
import CourseCard from "@/components/schedule/CourseCard";
import ProfessorCard from "@/components/schedule/ProfessorCard";
import ScheduleGrid from "@/components/schedule/ScheduleGrid";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Calendar, BookOpen, GraduationCap, Sparkles } from "lucide-react";

export default function ScheduleBuilder() {
  const [activeTab, setActiveTab] = useState("search");

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
            <CourseSearch />
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <CourseCard />
              <CourseCard />
            </div>

            <div className="text-center">
              <Button variant="outline" size="lg">
                Load More Courses
              </Button>
            </div>
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
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="text-yellow-600 text-xl">⚠️</div>
                <div>
                  <h3 className="font-semibold text-yellow-900">Schedule Conflicts Detected</h3>
                  <p className="text-sm text-yellow-800 mt-1">
                    No conflicts found! Your schedule looks great.
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

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <ProfessorCard />
              <ProfessorCard 
                professor={{
                  name: "Prof. Michael Chen",
                  grade_letter: "B",
                  composite_score: 85,
                  average_rating: 4.2,
                  average_difficulty: 3.8,
                  review_count: 32,
                  department: "Computer Science",
                  university: "City College"
                }}
              />
              <ProfessorCard 
                professor={{
                  name: "Dr. Emily Rodriguez",
                  grade_letter: "A",
                  composite_score: 95,
                  average_rating: 4.8,
                  average_difficulty: 2.9,
                  review_count: 68,
                  department: "Mathematics",
                  university: "Hunter College"
                }}
              />
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}