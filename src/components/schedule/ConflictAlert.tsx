import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Clock, MapPin } from "lucide-react";
import { TimeConflict } from "@/lib/supabase-queries";

interface ConflictAlertProps {
  conflicts: TimeConflict[];
  open: boolean;
  onClose: () => void;
  onProceed?: () => void;
  showProceedOption?: boolean;
}

export function ConflictAlert({
  conflicts,
  open,
  onClose,
  onProceed,
  showProceedOption = false,
}: ConflictAlertProps) {
  if (conflicts.length === 0) return null;

  return (
    <AlertDialog open={open} onOpenChange={onClose}>
      <AlertDialogContent className="max-w-2xl">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2 text-red-600">
            <AlertCircle className="h-5 w-5" />
            Schedule Conflict{conflicts.length > 1 ? 's' : ''} Detected
          </AlertDialogTitle>
          <AlertDialogDescription>
            The following section{conflicts.length > 1 ? 's' : ''} overlap with your current schedule:
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-4 max-h-96 overflow-y-auto">
          {conflicts.map((conflict, index) => (
            <Alert key={index} variant="destructive">
              <AlertDescription>
                <div className="space-y-3">
                  <div className="font-semibold text-red-900">
                    Conflict {index + 1}: Time Overlap
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    {/* Section 1 */}
                    <div className="bg-red-50 p-3 rounded border border-red-200">
                      <div className="font-medium text-red-900 mb-2">
                        Section {conflict.section1.section_number}
                      </div>
                      <div className="space-y-1 text-sm text-red-800">
                        {conflict.section1.professor_name && (
                          <div>Prof: {conflict.section1.professor_name}</div>
                        )}
                        {conflict.section1.days && conflict.section1.start_time && conflict.section1.end_time && (
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {conflict.section1.days} {conflict.section1.start_time} - {conflict.section1.end_time}
                          </div>
                        )}
                        {conflict.section1.location && (
                          <div className="flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {conflict.section1.location}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Section 2 */}
                    <div className="bg-red-50 p-3 rounded border border-red-200">
                      <div className="font-medium text-red-900 mb-2">
                        Section {conflict.section2.section_number}
                      </div>
                      <div className="space-y-1 text-sm text-red-800">
                        {conflict.section2.professor_name && (
                          <div>Prof: {conflict.section2.professor_name}</div>
                        )}
                        {conflict.section2.days && conflict.section2.start_time && conflict.section2.end_time && (
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {conflict.section2.days} {conflict.section2.start_time} - {conflict.section2.end_time}
                          </div>
                        )}
                        {conflict.section2.location && (
                          <div className="flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {conflict.section2.location}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          ))}
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel onClick={onClose}>Cancel</AlertDialogCancel>
          {showProceedOption && onProceed && (
            <AlertDialogAction
              onClick={onProceed}
              className="bg-red-600 hover:bg-red-700"
            >
              Add Anyway
            </AlertDialogAction>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface ConflictIndicatorProps {
  conflicts: TimeConflict[];
  className?: string;
}

export function ConflictIndicator({ conflicts, className = "" }: ConflictIndicatorProps) {
  if (conflicts.length === 0) return null;

  return (
    <div className={`flex items-center gap-2 text-red-600 ${className}`}>
      <AlertCircle className="h-4 w-4" />
      <span className="text-sm font-medium">
        {conflicts.length} conflict{conflicts.length > 1 ? 's' : ''}
      </span>
    </div>
  );
}
