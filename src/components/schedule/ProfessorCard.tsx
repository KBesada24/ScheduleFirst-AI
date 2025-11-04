import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Star, TrendingUp, BookOpen, Users } from "lucide-react";

interface ProfessorCardProps {
  professor?: {
    name: string;
    grade_letter: string;
    composite_score: number;
    average_rating: number;
    average_difficulty: number;
    review_count: number;
    department: string;
    university: string;
  };
}

export default function ProfessorCard({ 
  professor = {
    name: "Dr. Sarah Johnson",
    grade_letter: "A",
    composite_score: 92,
    average_rating: 4.6,
    average_difficulty: 3.2,
    review_count: 47,
    department: "Computer Science",
    university: "City College"
  }
}: ProfessorCardProps) {
  const getGradeColor = (grade: string) => {
    const colors: Record<string, string> = {
      'A': 'bg-green-500',
      'B': 'bg-blue-500',
      'C': 'bg-yellow-500',
      'D': 'bg-orange-500',
      'F': 'bg-red-500'
    };
    return colors[grade] || 'bg-gray-500';
  };

  const getDifficultyLabel = (difficulty: number) => {
    if (difficulty < 2.5) return { label: "Easy", color: "text-green-600" };
    if (difficulty < 3.5) return { label: "Moderate", color: "text-yellow-600" };
    return { label: "Challenging", color: "text-red-600" };
  };

  const difficultyInfo = getDifficultyLabel(professor.average_difficulty);

  return (
    <Card className="w-full bg-white hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-xl font-bold text-gray-900">
              {professor.name}
            </CardTitle>
            <p className="text-sm text-gray-600 mt-1">{professor.department}</p>
            <p className="text-xs text-gray-500">{professor.university}</p>
          </div>
          <div className={`${getGradeColor(professor.grade_letter)} text-white text-3xl font-bold rounded-lg w-16 h-16 flex items-center justify-center shadow-md`}>
            {professor.grade_letter}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Composite Score */}
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-600" />
              <span className="font-semibold text-gray-700">Overall Score</span>
            </div>
            <span className="text-2xl font-bold text-blue-600">{professor.composite_score}</span>
          </div>

          {/* Rating */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Star className="h-5 w-5 text-yellow-500 fill-yellow-500" />
              <span className="text-sm font-medium text-gray-700">Rating</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-lg font-bold text-gray-900">{professor.average_rating.toFixed(1)}</span>
              <span className="text-sm text-gray-500">/ 5.0</span>
            </div>
          </div>

          {/* Difficulty */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-purple-600" />
              <span className="text-sm font-medium text-gray-700">Difficulty</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-gray-900">{professor.average_difficulty.toFixed(1)}</span>
              <Badge variant="outline" className={difficultyInfo.color}>
                {difficultyInfo.label}
              </Badge>
            </div>
          </div>

          {/* Review Count */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">Reviews</span>
            </div>
            <span className="text-lg font-bold text-gray-900">{professor.review_count}</span>
          </div>

          {/* AI Recommendation */}
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm font-semibold text-blue-900 mb-1">AI Recommendation</p>
            <p className="text-sm text-blue-800">
              {professor.grade_letter === 'A' || professor.grade_letter === 'B' 
                ? "✅ Highly recommended! Students consistently praise this professor's teaching style."
                : professor.grade_letter === 'C'
                ? "⚠️ Mixed reviews. Consider your learning style and course requirements."
                : "❌ Consider alternative sections if available."}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}