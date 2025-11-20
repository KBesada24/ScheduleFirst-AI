import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Star, TrendingUp, BookOpen, Users, ThumbsUp, ThumbsDown } from "lucide-react";
import { ProfessorDetails } from "@/lib/api-endpoints";

interface ProfessorDetailModalProps {
  professor: ProfessorDetails | null;
  open: boolean;
  onClose: () => void;
  onCompare?: () => void;
}

export function ProfessorDetailModal({
  professor,
  open,
  onClose,
  onCompare,
}: ProfessorDetailModalProps) {
  if (!professor) return null;

  const hasReviews = professor.reviews && professor.reviews.length > 0;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl flex items-center gap-3">
            <div className="bg-blue-100 p-2 rounded-full">
              <Users className="h-6 w-6 text-blue-600" />
            </div>
            {professor.name}
          </DialogTitle>
          <DialogDescription>
            {professor.department && `${professor.department} • `}
            {professor.university || "CUNY"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Ratings Overview */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {professor.grade_letter && (
              <Card>
                <CardContent className="pt-6 text-center">
                  <div className="text-3xl font-bold text-blue-600">
                    {professor.grade_letter}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">Grade</div>
                </CardContent>
              </Card>
            )}

            {professor.average_rating !== null && professor.average_rating !== undefined && (
              <Card>
                <CardContent className="pt-6 text-center">
                  <div className="flex items-center justify-center gap-1">
                    <Star className="h-5 w-5 text-yellow-500 fill-yellow-500" />
                    <span className="text-3xl font-bold text-gray-900">
                      {professor.average_rating.toFixed(1)}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 mt-1">Rating</div>
                </CardContent>
              </Card>
            )}

            {professor.average_difficulty !== null && professor.average_difficulty !== undefined && (
              <Card>
                <CardContent className="pt-6 text-center">
                  <div className="flex items-center justify-center gap-1">
                    <TrendingUp className="h-5 w-5 text-orange-500" />
                    <span className="text-3xl font-bold text-gray-900">
                      {professor.average_difficulty.toFixed(1)}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 mt-1">Difficulty</div>
                </CardContent>
              </Card>
            )}

            {professor.review_count !== null && professor.review_count !== undefined && (
              <Card>
                <CardContent className="pt-6 text-center">
                  <div className="flex items-center justify-center gap-1">
                    <BookOpen className="h-5 w-5 text-green-500" />
                    <span className="text-3xl font-bold text-gray-900">
                      {professor.review_count}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 mt-1">Reviews</div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Composite Score */}
          {professor.composite_score !== null && professor.composite_score !== undefined && (
            <Card className="bg-gradient-to-r from-blue-50 to-purple-50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900">Composite Score</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      Overall rating based on multiple factors
                    </p>
                  </div>
                  <div className="text-4xl font-bold text-blue-600">
                    {professor.composite_score.toFixed(1)}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Reviews */}
          {hasReviews && (
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Student Reviews</h3>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {professor.reviews!.slice(0, 10).map((review, index) => (
                  <Card key={index}>
                    <CardContent className="pt-4">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {review.rating !== null && review.rating !== undefined && (
                            <Badge variant="secondary" className="flex items-center gap-1">
                              <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                              {review.rating.toFixed(1)}
                            </Badge>
                          )}
                          {review.difficulty !== null && review.difficulty !== undefined && (
                            <Badge variant="outline">
                              Difficulty: {review.difficulty.toFixed(1)}
                            </Badge>
                          )}
                        </div>
                        
                        {review.sentiment_positive !== null && review.sentiment_positive !== undefined && (
                          <div className="flex items-center gap-1">
                            {review.sentiment_positive > 0.5 ? (
                              <ThumbsUp className="h-4 w-4 text-green-600" />
                            ) : (
                              <ThumbsDown className="h-4 w-4 text-red-600" />
                            )}
                            <span className="text-xs text-gray-600">
                              {(review.sentiment_positive * 100).toFixed(0)}% positive
                            </span>
                          </div>
                        )}
                      </div>
                      
                      {review.review_text && (
                        <p className="text-sm text-gray-700">{review.review_text}</p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t">
            {onCompare && (
              <Button variant="outline" onClick={onCompare} className="flex-1">
                Compare Professors
              </Button>
            )}
            <Button onClick={onClose} className="flex-1">
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
