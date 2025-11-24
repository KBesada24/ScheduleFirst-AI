import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Clock, MapPin, Users, GraduationCap, Check } from "lucide-react";
import { CourseWithSections, TimeConflict } from "@/lib/supabase-queries";
import { ScheduleActionButton } from "@/components/ui/schedule-action-button";
import { ProfessorButton } from "@/components/ui/professor-button";
import { ProfessorDetails } from "@/lib/api-endpoints";
import { ConflictAlert } from "./ConflictAlert";

interface CourseCardProps {
  course?: CourseWithSections;
  scheduleId?: string;
  currentSections?: string[];
  onScheduleUpdate?: () => void;
  showAddButton?: boolean;
}

export default function CourseCard({
  course,
  scheduleId,
  currentSections = [],
  onScheduleUpdate,
  showAddButton = true,
}: CourseCardProps) {
  const [conflicts, setConflicts] = useState<TimeConflict[]>([]);
  const [showConflictDialog, setShowConflictDialog] = useState(false);
  const [addedSections, setAddedSections] = useState<Set<string>>(new Set());

  if (!course) return null;

  const handleAddSuccess = (sectionId: string) => {
    setAddedSections(prev => new Set(prev).add(sectionId));
    if (onScheduleUpdate) {
      onScheduleUpdate();
    }
  };

  const handleConflict = (detectedConflicts: TimeConflict[]) => {
    setConflicts(detectedConflicts);
    setShowConflictDialog(true);
  };

  const isSectionInSchedule = (sectionId: string) => {
    return currentSections.includes(sectionId) || addedSections.has(sectionId);
  };

  return (
    <>
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
            {course.sections.map((section) => {
              const isInSchedule = isSectionInSchedule(section.id);

              return (
                <div
                  key={section.id}
                  className="p-3 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-gray-900">
                      Section {section.section_number}
                    </span>
                    <div className="flex items-center gap-2">
                      <Badge variant={section.modality === "Online" ? "default" : "outline"}>
                        {section.modality}
                      </Badge>
                      {isInSchedule && (
                        <Badge variant="default" className="bg-green-600">
                          <Check className="h-3 w-3 mr-1" />
                          Added
                        </Badge>
                      )}
                    </div>
                  </div>

                  <div className="space-y-1 text-sm mb-3">
                    {section.professor_name && (
                      <div className="flex items-center gap-2 text-gray-700">
                        <ProfessorButton
                          professorName={section.professor_name}
                          onDataLoaded={(data: ProfessorDetails) => {
                            console.log("Professor data loaded:", data);
                            // Future: Show professor details modal
                          }}
                          className="p-0 h-auto font-normal text-gray-700 hover:text-blue-600 hover:no-underline"
                        />
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

                  {/* Add to Schedule Button */}
                  {showAddButton && scheduleId && (
                    <ScheduleActionButton
                      action="add"
                      sectionId={section.id}
                      scheduleId={scheduleId}
                      currentSections={currentSections}
                      onSuccess={() => handleAddSuccess(section.id)}
                      onConflict={handleConflict}
                      disabled={isInSchedule}
                      size="sm"
                      className="w-full"
                    />
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>

        {/* Conflict Alert Dialog */}
        <ConflictAlert
          conflicts={conflicts}
          open={showConflictDialog}
          onClose={() => setShowConflictDialog(false)}
        />
      </Card>
    </>
  );
}