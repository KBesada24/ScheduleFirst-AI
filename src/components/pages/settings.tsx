import { useState, useEffect } from "react";
import { useAuth } from "../../../supabase/auth";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { UniversityDropdown } from "@/components/ui/university-dropdown";
import { useToast } from "@/components/ui/use-toast";
import { Loader2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import Sidebar from "../dashboard/layout/Sidebar";
import TopNavigation from "../dashboard/layout/TopNavigation";

export default function SettingsPage() {
  const { user, profile, updateUniversity } = useAuth();
  const [loading, setLoading] = useState(false);
  const [selectedUniversity, setSelectedUniversity] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    if (profile?.university) {
      setSelectedUniversity(profile.university);
    }
  }, [profile]);

  const handleSave = async () => {
    setLoading(true);
    try {
      await updateUniversity(selectedUniversity);
      toast({
        title: "Success",
        description: "Your university preference has been updated.",
      });
      setIsEditing(false);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update university.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <TopNavigation />
      <div className="flex h-[calc(100vh-64px)] mt-16">
        <Sidebar activeItem="Settings" />
        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-2xl mx-auto space-y-6">
            <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
            
            <Card>
              <CardHeader>
                <CardTitle>Profile Settings</CardTitle>
                <CardDescription>
                  Manage your personal information and preferences.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">Email</label>
                  <div className="p-2 bg-gray-100 rounded-md text-gray-600">
                    {user?.email}
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">University</label>
                  {isEditing ? (
                    <UniversityDropdown
                      value={selectedUniversity}
                      onChange={setSelectedUniversity}
                      disabled={loading}
                    />
                  ) : (
                    <div className="flex items-center justify-between p-2 bg-gray-50 border rounded-md">
                      <span className="text-gray-900 font-medium">
                        {profile?.university || "Not set"}
                      </span>
                      <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
                        Change
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
              <CardFooter className="flex justify-end gap-2">
                {isEditing && (
                  <>
                    <Button variant="outline" onClick={() => {
                      setIsEditing(false);
                      setSelectedUniversity(profile?.university || "");
                    }}>
                      Cancel
                    </Button>
                    
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button disabled={loading || selectedUniversity === profile?.university}>
                          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                          Save Changes
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                          <AlertDialogDescription>
                            Changing your university will update your course searches and schedule recommendations.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={handleSave}>Continue</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </>
                )}
              </CardFooter>
            </Card>
          </div>
        </main>
      </div>
    </div>
  );
}
