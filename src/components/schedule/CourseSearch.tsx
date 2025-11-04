import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, Filter } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface CourseSearchProps {
  onSearch?: (query: string, filters: any) => void;
}

export default function CourseSearch({ onSearch }: CourseSearchProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [department, setDepartment] = useState("all");
  const [modality, setModality] = useState("all");
  const [timeSlot, setTimeSlot] = useState("all");

  const handleSearch = () => {
    onSearch?.(searchQuery, { department, modality, timeSlot });
  };

  return (
    <Card className="w-full bg-white">
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* Search Bar */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search courses (e.g., CSC 381, Algorithms, Computer Science)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <Button onClick={handleSearch} className="bg-blue-600 hover:bg-blue-700">
              Search
            </Button>
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
                <SelectItem value="in-person">In-Person</SelectItem>
                <SelectItem value="online">Online</SelectItem>
                <SelectItem value="hybrid">Hybrid</SelectItem>
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

            <Button variant="outline" size="sm" onClick={() => {
              setDepartment("all");
              setModality("all");
              setTimeSlot("all");
              setSearchQuery("");
            }}>
              Clear Filters
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}