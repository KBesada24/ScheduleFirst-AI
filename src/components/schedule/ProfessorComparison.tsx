import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Star, TrendingUp, BookOpen, Award } from "lucide-react";
import { ProfessorDetails } from "@/lib/api-endpoints";

interface ProfessorComparisonProps {
  professors: ProfessorDetails[];
  highlightBest?: boolean;
}

export function ProfessorComparison({
  professors,
  highlightBest = true,
}: ProfessorComparisonProps) {
  if (professors.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-gray-500">
          No professors to compare
        </CardContent>
      </Card>
    );
  }

  // Find best professor based on composite score
  const bestProfessor = highlightBest
    ? professors.reduce((best, current) => {
        const bestScore = best.composite_score || 0;
        const currentScore = current.composite_score || 0;
        return currentScore > bestScore ? current : best;
      }, professors[0])
    : null;

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-900">Professor Comparison</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {professors.map((professor) => {
          const isBest = bestProfessor && professor.id === bestProfessor.id;
          
          return (
            <Card 
              key={professor.id}
              className={isBest ? "ring-2 ring-green-500 shadow-lg" : ""}
            >
              <CardHeader>
                <CardTitle className="text-lg flex items-center justify-between">
                  <span className="truncate">{professor.name}</span>
                  {isBest && (
                    <Badge className="bg-green-600 ml-2">
                      <Award className="h-3 w-3 mr-1" />
                      Best
                    </Badge>
                  )}
                </CardTitle>
                {professor.department && (
                  <p className="text-sm text-gray-600">{professor.department}</p>
                )}
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Key Metrics */}
                <div className="grid grid-cols-2 gap-3">
                  {/* Grade */}
                  {professor.grade_letter && (
                    <div className="text-center p-3 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {professor.grade_letter}
                      </div>
                      <div className="text-xs text-gray-600 mt-1">Grade</div>
                    </div>
                  )}

                  {/* Rating */}
                  {professor.average_rating !== null && professor.average_rating !== undefined && (
                    <div className="text-center p-3 bg-yellow-50 rounded-lg">
                      <div className="flex items-center justify-center gap-1">
                        <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                        <span className="text-2xl font-bold text-gray-900">
                          {professor.average_rating.toFixed(1)}
                        </span>
                      </div>
                      <div className="text-xs text-gray-600 mt-1">Rating</div>
                    </div>
                  )}

                  {/* Difficulty */}
                  {professor.average_difficulty !== null && professor.average_difficulty !== undefined && (
                    <div className="text-center p-3 bg-orange-50 rounded-lg">
                      <div className="flex items-center justify-center gap-1">
                        <TrendingUp className="h-4 w-4 text-orange-500" />
                        <span className="text-2xl font-bold text-gray-900">
                          {professor.average_difficulty.toFixed(1)}
                        </span>
                      </div>
                      <div className="text-xs text-gray-600 mt-1">Difficulty</div>
                    </div>
                  )}

                  {/* Reviews */}
                  {professor.review_count !== null && professor.review_count !== undefined && (
                    <div className="text-center p-3 bg-green-50 rounded-lg">
                      <div className="flex items-center justify-center gap-1">
                        <BookOpen className="h-4 w-4 text-green-500" />
                        <span className="text-2xl font-bold text-gray-900">
                          {professor.review_count}
                        </span>
                      </div>
                      <div className="text-xs text-gray-600 mt-1">Reviews</div>
                    </div>
                  )}
                </div>

                {/* Composite Score */}
                {professor.composite_score !== null && professor.composite_score !== undefined && (
                  <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-3 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">
                        Composite Score
                      </span>
                      <span className="text-2xl font-bold text-blue-600">
                        {professor.composite_score.toFixed(1)}
                      </span>
                    </div>
                  </div>
                )}

                {/* AI Recommendation */}
                {isBest && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <p className="text-sm text-green-900">
                      <strong>AI Recommendation:</strong> This professor has the highest
                      overall rating based on student reviews and performance metrics.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Summary */}
      {highlightBest && bestProfessor && (
        <Card className="bg-gradient-to-r from-green-50 to-blue-50">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <Award className="h-6 w-6 text-green-600 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900">Recommended Choice</h3>
                <p className="text-sm text-gray-700 mt-1">
                  Based on the comparison, <strong>{bestProfessor.name}</strong> appears
                  to be the best choice with a composite score of{" "}
                  <strong>{bestProfessor.composite_score?.toFixed(1)}</strong>.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
