import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Check, AlertCircle, Star, Clock, Calendar, TrendingUp } from "lucide-react";
import { OptimizedSchedule } from "@/lib/api-endpoints";

interface ScheduleOptionCardProps {
  schedule: OptimizedSchedule;
  index: number;
  isSelected?: boolean;
  onSelect?: () => void;
  onApply?: () => void;
}

export function ScheduleOptionCard({
  schedule,
  index,
  isSelected = false,
  onSelect,
  onApply,
}: ScheduleOptionCardProps) {
  const hasConflicts = schedule.conflicts && schedule.conflicts.length > 0;

  return (
    <Card 
      className={`cursor-pointer transition-all ${
        isSelected 
          ? 'ring-2 ring-blue-500 shadow-lg' 
          : 'hover:shadow-md'
      }`}
      onClick={onSelect}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg flex items-center gap-2">
              Schedule Option {index + 1}
              {isSelected && (
                <Badge variant="default" className="bg-blue-600">
                  <Check className="h-3 w-3 mr-1" />
                  Selected
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="mt-1">
              {schedule.sections.length} section{schedule.sections.length !== 1 ? 's' : ''}
            </CardDescription>
          </div>
          
          <div className="flex items-center gap-2">
            <Badge 
              variant={hasConflicts ? "destructive" : "secondary"}
              className="text-lg font-bold"
            >
              <TrendingUp className="h-4 w-4 mr-1" />
              {schedule.score ? schedule.score.toFixed(1) : 'N/A'}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Metadata */}
        {schedule.metadata && (
          <div className="grid grid-cols-2 gap-3">
            {schedule.metadata.avgProfessorRating !== undefined && (
              <div className="flex items-center gap-2 text-sm">
                <Star className="h-4 w-4 text-yellow-500" />
                <span className="text-gray-600">
                  Avg Rating: <span className="font-semibold text-gray-900">
                    {schedule.metadata.avgProfessorRating.toFixed(1)}
                  </span>
                </span>
              </div>
            )}
            
            {schedule.metadata.totalCredits !== undefined && (
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="h-4 w-4 text-blue-500" />
                <span className="text-gray-600">
                  Credits: <span className="font-semibold text-gray-900">
                    {schedule.metadata.totalCredits}
                  </span>
                </span>
              </div>
            )}
            
            {schedule.metadata.daysPerWeek !== undefined && (
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="h-4 w-4 text-green-500" />
                <span className="text-gray-600">
                  Days/Week: <span className="font-semibold text-gray-900">
                    {schedule.metadata.daysPerWeek}
                  </span>
                </span>
              </div>
            )}
            
            {schedule.metadata.gapHours !== undefined && (
              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-purple-500" />
                <span className="text-gray-600">
                  Gap Hours: <span className="font-semibold text-gray-900">
                    {schedule.metadata.gapHours.toFixed(1)}
                  </span>
                </span>
              </div>
            )}
          </div>
        )}

        {/* Reasoning */}
        {schedule.reasoning && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-sm text-blue-900">{schedule.reasoning}</p>
          </div>
        )}

        {/* Conflicts */}
        {hasConflicts && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-red-900">
                  {schedule.conflicts.length} Conflict{schedule.conflicts.length !== 1 ? 's' : ''}
                </p>
                <p className="text-xs text-red-700 mt-1">
                  Some courses overlap in this schedule
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          {onSelect && !isSelected && (
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onSelect();
              }}
              className="flex-1"
            >
              Preview
            </Button>
          )}
          
          {onApply && (
            <Button
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onApply();
              }}
              className="flex-1 bg-blue-600 hover:bg-blue-700"
              disabled={hasConflicts}
            >
              Apply to My Schedule
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
