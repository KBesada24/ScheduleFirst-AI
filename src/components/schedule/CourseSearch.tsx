import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Filter, AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { SearchButton } from "@/components/ui/search-button";
import { CourseWithSections } from "@/lib/supabase-queries";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import CourseCard from "./CourseCard";

interface CourseSearchProps {
  onSearch?: (query: string, filters: any) => void;
}

export default function CourseSearch({ onSearch }: CourseSearchProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [searchQuery, setSearchQuery] = useState(searchParams.get("query") || "");
  const [department, setDepartment] = useState(searchParams.get("department") || "all");
  const [modality, setModality] = useState(searchParams.get("modality") || "all");
  const [timeSlot, setTimeSlot] = useState(searchParams.get("timeSlot") || "all");
  const [courses, setCourses] = useState<CourseWithSections[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Update URL params when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    
    if (searchQuery) params.set("query", searchQuery);
    if (department !== "all") params.set("department", department);
    if (modality !== "all") params.set("modality", modality);
    if (timeSlot !== "all") params.set("timeSlot", timeSlot);
    
    setSearchParams(params, { replace: true });
  }, [searchQuery, department, modality, timeSlot, setSearchParams]);

  const handleSearchResults = (results: CourseWithSections[]) => {
    setCourses(results);
    setError(null);
    setHasSearched(true);
    setLoading(false);
    onSearch?.(searchQuery, { department, modality, timeSlot });
  };

  const handleSearchError = (err: Error) => {
    setError(err);
    setCourses([]);
    setHasSearched(true);
    setLoading(false);
  };

  const handleClearFilters = () => {
    setDepartment("all");
    setModality("all");
    setTimeSlot("all");
    setSearchQuery("");
    setCourses([]);
    setError(null);
    setHasSearched(false);
  };

  return (
    <div className="space-y-4">
      <Card className="w-full bg-white">
        <CardContent className="pt-6">
          <div className="space-y-4">
            {/* Search Bar */}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  placeholder="Search courses (e.g., CSC 381, Algorithms, Computer Science)"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      setLoading(true);
                    }
                  }}
                />
              </div>
              <SearchButton
                query={searchQuery}
                filters={{ department, modality, timeSlot }}
                onResults={handleSearchResults}
                onError={handleSearchError}
                disabled={loading}
              />
            </div>

            {/* Filters */}
            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="h-4 w-4 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">Filters:</span>
              
              <Select value={department} onValueChange={setDepartment}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Department" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Departments</SelectItem>
                  <SelectItem value="csc">Computer Science</SelectItem>
                  <SelectItem value="math">Mathematics</SelectItem>
                  <SelectItem value="eng">English</SelectItem>
                  <SelectItem value="bio">Biology</SelectItem>
                  <SelectItem value="chem">Chemistry</SelectItem>
                  <SelectItem value="phys">Physics</SelectItem>
                </SelectContent>
              </Select>

              <Select value={modality} onValueChange={setModality}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Modality" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Modalities</SelectItem>
                  <SelectItem value="In-person">In-Person</SelectItem>
                  <SelectItem value="Online">Online</SelectItem>
                  <SelectItem value="Hybrid">Hybrid</SelectItem>
                </SelectContent>
              </Select>

              <Select value={timeSlot} onValueChange={setTimeSlot}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Time Slot" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Times</SelectItem>
                  <SelectItem value="morning">Morning (8AM-12PM)</SelectItem>
                  <SelectItem value="afternoon">Afternoon (12PM-5PM)</SelectItem>
                  <SelectItem value="evening">Evening (5PM-9PM)</SelectItem>
                </SelectContent>
              </Select>

              <button
                className="text-sm text-blue-600 hover:text-blue-700 underline"
                onClick={handleClearFilters}
              >
                Clear Filters
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner className="h-8 w-8" />
          <span className="ml-2 text-gray-600">Searching courses...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error.message || "Failed to search courses. Please try again."}
          </AlertDescription>
        </Alert>
      )}

      {/* No Results */}
      {hasSearched && !loading && !error && courses.length === 0 && (
        <Card className="w-full bg-white">
          <CardContent className="py-8">
            <div className="text-center text-gray-600">
              <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
              <p className="text-lg font-medium">No courses found</p>
              <p className="text-sm mt-1">Try adjusting your search criteria or filters</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {!loading && courses.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Found {courses.length} course{courses.length !== 1 ? 's' : ''}
          </p>
          {courses.map((course) => (
            <CourseCard key={course.id} course={course} />
          ))}
        </div>
      )}
    </div>
  );
}