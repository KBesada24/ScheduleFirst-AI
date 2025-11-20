import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Clock, MapPin, Users, GraduationCap } from "lucide-react";

import { CourseWithSections } from "@/lib/supabase-queries";

interface CourseCardProps {
  course?: CourseWithSections;
}

export default function CourseCard({ course }: CourseCardProps) {
  if (!course) return null;
  return (
    <Card className="w-full bg-white hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-xl font-bold text-gray-900">
              {course.course_code}
            </CardTitle>
            <CardDescription className="text-base mt-1">
              {course.name}
            </CardDescription>
          </div>
          <Badge variant="secondary" className="ml-2">
            {course.credits} Credits
          </Badge>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <GraduationCap className="h-4 w-4 text-gray-500" />
          <span className="text-sm text-gray-600">{course.department}</span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <h4 className="font-semibold text-sm text-gray-700">Available Sections:</h4>
          {course.sections.map((section) => (
            <div
              key={section.id}
              className="p-3 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-gray-900">
                  Section {section.section_number}
                </span>
                <Badge variant={section.modality === "Online" ? "default" : "outline"}>
                  {section.modality}
                </Badge>
              </div>
              
              <div className="space-y-1 text-sm">
                {section.professor_name && (
                  <div className="flex items-center gap-2 text-gray-700">
                    <GraduationCap className="h-4 w-4" />
                    <span>{section.professor_name}</span>
                  </div>
                )}
                
                {section.days && section.start_time && section.end_time && (
                  <div className="flex items-center gap-2 text-gray-600">
                    <Clock className="h-4 w-4" />
                    <span>{section.days} {section.start_time} - {section.end_time}</span>
                  </div>
                )}
                
                {section.location && (
                  <div className="flex items-center gap-2 text-gray-600">
                    <MapPin className="h-4 w-4" />
                    <span>{section.location}</span>
                  </div>
                )}
                
                {section.enrolled !== null && section.capacity !== null && (
                  <div className="flex items-center gap-2 text-gray-600">
                    <Users className="h-4 w-4" />
                    <span>{section.enrolled}/{section.capacity} enrolled</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}