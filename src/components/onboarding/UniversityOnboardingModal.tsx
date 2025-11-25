import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { UniversityDropdown } from "@/components/ui/university-dropdown";
import { useAuth } from "../../../supabase/auth";
import { Loader2 } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

export function UniversityOnboardingModal() {
  const { user, profile, updateUniversity, loading: authLoading } = useAuth();
  const [selectedUniversity, setSelectedUniversity] = useState("");
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  // Only show if user is logged in, auth is done loading, profile is loaded, and university is missing
  if (authLoading || !user || !profile || profile.university) return null;

  const handleSave = async () => {
    if (!selectedUniversity) return;
    
    setLoading(true);
    try {
      await updateUniversity(selectedUniversity);
      toast({
        title: "Welcome!",
        description: `Your school has been set to ${selectedUniversity}.`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save university. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={true} onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-[425px]" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>Welcome to ScheduleFirst AI!</DialogTitle>
          <DialogDescription>
            To get started, please tell us which CUNY school you attend. This helps us find the right courses for you.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <UniversityDropdown 
            value={selectedUniversity} 
            onChange={setSelectedUniversity}
            disabled={loading}
          />
        </div>
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={!selectedUniversity || loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Get Started
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
