import { useState, useRef, useEffect } from "react";
import CourseSearch from "@/components/schedule/CourseSearch";
import CourseCard from "@/components/schedule/CourseCard";
import ProfessorCard from "@/components/schedule/ProfessorCard";
import ScheduleGrid from "@/components/schedule/ScheduleGrid";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Calendar, BookOpen, GraduationCap, Sparkles, MessageSquare, Send } from "lucide-react";
import { useCourseSearch, useProfessorSearch } from "@/lib/supabase-hooks";
import { useScheduleGrid } from "@/hooks/useScheduleGrid";
import { OptimizeButton } from "@/components/ui/optimize-button";
import { ScheduleOptimizationResponse, sendChatMessage } from "@/lib/api-endpoints";
import { useAuth } from "../../../supabase/auth";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  suggestedSchedule?: any;
};

export default function ScheduleBuilder() {
  const [activeTab, setActiveTab] = useState("search");
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState({
    department: "all",
    modality: "all",
    timeSlot: "all",
  });
  const [chatMessages, setChatMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "Hi! I'm your AI scheduling assistant. I can help you build an optimal schedule based on your preferences. What courses are you interested in taking this semester?",
      timestamp: new Date(),
    },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isAiThinking, setIsAiThinking] = useState(false);
  const { profile } = useAuth();
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Schedule grid management
  const {
    sections,
    conflicts,
    isUpdating,
    updateFromAI,
  } = useScheduleGrid();

  // Fetch courses based on search
  const { courses, loading: coursesLoading } = useCourseSearch({
    query: searchQuery,
    department: filters.department !== "all" ? filters.department : undefined,
    semester: "Current Semester",
    university: profile?.university || undefined,
    limit: 20,
  });

  // Fetch top professors
  const { professors, loading: professorsLoading } = useProfessorSearch({
    limit: 10,
    university: profile?.university || undefined,
  });

  const handleSearch = (query: string, newFilters: any) => {
    setSearchQuery(query);
    setFilters(newFilters);
  };

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  const handleSendMessage = async () => {
    if (!chatInput.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: chatInput,
      timestamp: new Date(),
    };

    setChatMessages((prev) => [...prev, userMessage]);
    setChatInput("");
    setIsAiThinking(true);

    try {
      // Use ChatButton's API call
      const response = await sendChatMessage({
        message: chatInput,
        context: {
          currentSchedule: sections.length > 0 ? {
            sections: sections,
            count: sections.length,
          } : undefined,
          semester: "Fall 2025",
          preferences: {
            // Add any user preferences here
          },
        },
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.message,
        timestamp: new Date(),
        suggestedSchedule: response.suggestedSchedule,
      };

      setChatMessages(prev => [...prev, assistantMessage]);

      // Handle suggestions if any
      if (response.suggestedSchedule) {
        // Display suggestion UI
        console.log('AI suggested schedule:', response.suggestedSchedule);
        // Update the calendar grid with AI-suggested schedule
        await updateFromAI(response.suggestedSchedule);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      };
      setChatMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsAiThinking(false);
    }
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
          {/* University Display */}
          <div className="flex items-center justify-center gap-2">
            <span className="text-sm font-medium text-gray-700">
              School: <span className="font-bold text-blue-600">{profile?.university || "Not set"}</span>
            </span>
          </div>
        </div>

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4 max-w-3xl mx-auto">
            <TabsTrigger value="search" className="flex items-center gap-2">
              <BookOpen className="h-4 w-4" />
              Course Search
            </TabsTrigger>
            <TabsTrigger value="schedule" className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              My Schedule
            </TabsTrigger>
            <TabsTrigger value="ai-chat" className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              AI Assistant
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
                      course={course}
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
                <h2 className="text-2xl font-bold text-gray-900">Current Semester Schedule</h2>
                <p className="text-gray-600"></p>
              </div>
              <div className="flex gap-2">
                <OptimizeButton
                  courseCodes={sections.map(s => s.course_id)} // Using course_id as proxy for code for now
                  semester="Fall 2025"
                  university="Baruch College"
                  onOptimized={(response: ScheduleOptimizationResponse) => {
                    console.log("Optimization complete:", response);
                    // Here we would update the schedule with the optimized result
                    // For now, just log it
                  }}
                  className="bg-white text-black border border-input hover:bg-accent hover:text-accent-foreground"
                />
                <Button className="bg-blue-600 hover:bg-blue-700">
                  Save Schedule
                </Button>
              </div>
            </div>

            <ScheduleGrid
              sections={sections}
              conflicts={conflicts}
              editable={true}
            />

            {/* Conflict Detection Alert */}
            {conflicts.length === 0 ? (
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
            ) : (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="text-red-600 text-xl">⚠️</div>
                  <div>
                    <h3 className="font-semibold text-red-900">
                      {conflicts.length} Schedule Conflict{conflicts.length > 1 ? 's' : ''} Detected
                    </h3>
                    <p className="text-sm text-red-800 mt-1">
                      Some courses overlap. Please review your schedule and remove conflicting courses.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </TabsContent>

          {/* AI Chat Tab */}
          <TabsContent value="ai-chat" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Chat Section */}
              <Card className="flex flex-col h-[600px]">
                <CardContent className="flex flex-col h-full p-0">
                  <div className="border-b p-4 bg-gradient-to-r from-blue-600 to-purple-600">
                    <h3 className="font-semibold text-white flex items-center gap-2">
                      <Sparkles className="h-5 w-5" />
                      AI Scheduling Assistant
                    </h3>
                    <p className="text-sm text-blue-100 mt-1">
                      Ask me anything about courses, schedules, or professors
                    </p>
                  </div>

                  {/* Messages */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {chatMessages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-lg p-3 ${message.role === "user"
                            ? "bg-blue-600 text-white"
                            : "bg-gray-100 text-gray-900"
                            }`}
                        >
                          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                          <p
                            className={`text-xs mt-1 ${message.role === "user" ? "text-blue-100" : "text-gray-500"
                              }`}
                          >
                            {message.timestamp.toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        </div>
                      </div>
                    ))}

                    {isAiThinking && (
                      <div className="flex justify-start">
                        <div className="bg-gray-100 rounded-lg p-3">
                          <div className="flex gap-1">
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.4s]" />
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  {/* Input */}
                  <div className="border-t p-4">
                    <div className="flex gap-2">
                      <Input
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
                        placeholder="Ask about courses, schedules, or professors..."
                        className="flex-1"
                        disabled={isAiThinking}
                      />
                      <Button
                        onClick={handleSendMessage}
                        disabled={isAiThinking || !chatInput.trim()}
                        className="bg-blue-600 hover:bg-blue-700"
                      >
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Schedule Preview */}
              <div className="space-y-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold text-gray-900">AI Suggested Schedule</h3>
                      <Button size="sm" variant="outline">
                        Apply to My Schedule
                      </Button>
                    </div>

                    {/* Mini Calendar Grid */}
                    <div className="bg-white border rounded-lg overflow-hidden">
                      <div className="grid grid-cols-6 bg-gray-50 border-b">
                        <div className="p-2 text-xs font-medium text-gray-600 border-r">Time</div>
                        <div className="p-2 text-xs font-medium text-gray-600 text-center border-r">Mon</div>
                        <div className="p-2 text-xs font-medium text-gray-600 text-center border-r">Tue</div>
                        <div className="p-2 text-xs font-medium text-gray-600 text-center border-r">Wed</div>
                        <div className="p-2 text-xs font-medium text-gray-600 text-center border-r">Thu</div>
                        <div className="p-2 text-xs font-medium text-gray-600 text-center">Fri</div>
                      </div>

                      {/* Time slots */}
                      {["9:00", "10:00", "11:00", "12:00", "1:00", "2:00", "3:00"].map((time) => (
                        <div key={time} className="grid grid-cols-6 border-b last:border-b-0">
                          <div className="p-2 text-xs text-gray-600 border-r bg-gray-50">{time}</div>
                          <div className="p-2 border-r min-h-[60px]">
                            {time === "10:00" && (
                              <div className="bg-blue-100 border border-blue-300 rounded p-1 text-xs">
                                <div className="font-medium text-blue-900">CSC 101</div>
                                <div className="text-blue-700">10:00-11:00</div>
                              </div>
                            )}
                          </div>
                          <div className="p-2 border-r min-h-[60px]">
                            {time === "1:00" && (
                              <div className="bg-purple-100 border border-purple-300 rounded p-1 text-xs">
                                <div className="font-medium text-purple-900">MAT 201</div>
                                <div className="text-purple-700">1:00-2:30</div>
                              </div>
                            )}
                          </div>
                          <div className="p-2 border-r min-h-[60px]">
                            {time === "10:00" && (
                              <div className="bg-blue-100 border border-blue-300 rounded p-1 text-xs">
                                <div className="font-medium text-blue-900">CSC 101</div>
                                <div className="text-blue-700">10:00-11:00</div>
                              </div>
                            )}
                            {time === "2:00" && (
                              <div className="bg-green-100 border border-green-300 rounded p-1 text-xs">
                                <div className="font-medium text-green-900">ENG 102</div>
                                <div className="text-green-700">2:00-3:30</div>
                              </div>
                            )}
                          </div>
                          <div className="p-2 border-r min-h-[60px]">
                            {time === "1:00" && (
                              <div className="bg-purple-100 border border-purple-300 rounded p-1 text-xs">
                                <div className="font-medium text-purple-900">MAT 201</div>
                                <div className="text-purple-700">1:00-2:30</div>
                              </div>
                            )}
                          </div>
                          <div className="p-2 min-h-[60px]">
                            {time === "10:00" && (
                              <div className="bg-blue-100 border border-blue-300 rounded p-1 text-xs">
                                <div className="font-medium text-blue-900">CSC 101</div>
                                <div className="text-blue-700">10:00-11:00</div>
                              </div>
                            )}
                            {time === "2:00" && (
                              <div className="bg-green-100 border border-green-300 rounded p-1 text-xs">
                                <div className="font-medium text-green-900">ENG 102</div>
                                <div className="text-green-700">2:00-3:30</div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Course Summary */}
                    <div className="mt-4 space-y-2">
                      <h4 className="text-sm font-medium text-gray-900">Recommended Courses</h4>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between p-2 bg-blue-50 rounded">
                          <div>
                            <div className="text-sm font-medium text-blue-900">CSC 101</div>
                            <div className="text-xs text-blue-700">MWF 10:00-11:00 • 3 credits</div>
                          </div>
                          <div className="text-xs font-medium text-blue-900">Grade: A</div>
                        </div>
                        <div className="flex items-center justify-between p-2 bg-purple-50 rounded">
                          <div>
                            <div className="text-sm font-medium text-purple-900">MAT 201</div>
                            <div className="text-xs text-purple-700">TTh 1:00-2:30 • 4 credits</div>
                          </div>
                          <div className="text-xs font-medium text-purple-900">Grade: A-</div>
                        </div>
                        <div className="flex items-center justify-between p-2 bg-green-50 rounded">
                          <div>
                            <div className="text-sm font-medium text-green-900">ENG 102</div>
                            <div className="text-xs text-green-700">MW 2:00-3:30 • 3 credits</div>
                          </div>
                          <div className="text-xs font-medium text-green-900">Grade: B+</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
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
                      university: profile?.university || "Baruch College",
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