import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { seedDatabase, clearDatabase } from "@/lib/seed-database";
import { Database, Trash2, CheckCircle, AlertCircle } from "lucide-react";

export default function AdminPage() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSeed = async () => {
    setLoading(true);
    setMessage(null);
    try {
      await seedDatabase();
      setMessage({ type: "success", text: "Database seeded successfully! Check the console for details." });
    } catch (error) {
      setMessage({ type: "error", text: `Error seeding database: ${error}` });
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    if (!confirm("Are you sure you want to clear ALL data? This cannot be undone!")) {
      return;
    }

    setLoading(true);
    setMessage(null);
    try {
      await clearDatabase();
      setMessage({ type: "success", text: "Database cleared successfully!" });
    } catch (error) {
      setMessage({ type: "error", text: `Error clearing database: ${error}` });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-gray-900">Admin Panel</h1>
          <p className="text-lg text-gray-600">Database Management Tools</p>
        </div>

        {message && (
          <div
            className={`p-4 rounded-lg border ${
              message.type === "success"
                ? "bg-green-50 border-green-200 text-green-800"
                : "bg-red-50 border-red-200 text-red-800"
            }`}
          >
            <div className="flex items-center gap-2">
              {message.type === "success" ? (
                <CheckCircle className="h-5 w-5" />
              ) : (
                <AlertCircle className="h-5 w-5" />
              )}
              <p>{message.text}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="bg-white">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Database className="h-6 w-6 text-blue-600" />
                <CardTitle>Seed Database</CardTitle>
              </div>
              <CardDescription>
                Populate the database with sample courses, professors, sections, and reviews for testing.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                onClick={handleSeed}
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700"
              >
                {loading ? "Seeding..." : "Seed Database"}
              </Button>
              <div className="mt-4 text-sm text-gray-600 space-y-1">
                <p>This will create:</p>
                <ul className="list-disc list-inside ml-2">
                  <li>4 sample professors</li>
                  <li>4 sample courses</li>
                  <li>6 course sections</li>
                  <li>4 professor reviews</li>
                </ul>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Trash2 className="h-6 w-6 text-red-600" />
                <CardTitle>Clear Database</CardTitle>
              </div>
              <CardDescription>
                Remove all data from the database. This action cannot be undone!
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                onClick={handleClear}
                disabled={loading}
                variant="destructive"
                className="w-full"
              >
                {loading ? "Clearing..." : "Clear Database"}
              </Button>
              <div className="mt-4 text-sm text-red-600 space-y-1">
                <p className="font-semibold">⚠️ Warning:</p>
                <p>This will permanently delete all courses, professors, sections, reviews, and schedules.</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="bg-white">
          <CardHeader>
            <CardTitle>Database Schema</CardTitle>
            <CardDescription>Current tables in the database</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {["users", "courses", "course_sections", "professors", "professor_reviews", "user_schedules"].map(
                (table) => (
                  <div key={table} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="font-mono text-sm text-gray-700">{table}</p>
                  </div>
                )
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
