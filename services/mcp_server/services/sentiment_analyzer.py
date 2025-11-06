"""
Sentiment analysis service for professor reviews
Uses Hugging Face transformers for aspect-based sentiment analysis
"""
from typing import List, Dict, Optional
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

from ..config import settings
from ..utils.logger import get_logger


logger = get_logger(__name__)


class SentimentAnalyzer:
    """Analyze sentiment in professor reviews"""
    
    def __init__(self):
        self.model_name = settings.sentiment_model_name
        self.pipeline = None
        self._load_model()
        logger.info(f"Sentiment analyzer initialized with model: {self.model_name}")
    
    def _load_model(self):
        """Load the sentiment analysis model"""
        try:
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model_name,
                device=0 if torch.cuda.is_available() else -1
            )
            logger.info("Sentiment model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading sentiment model: {e}")
            raise
    
    def analyze_review(self, review_text: str) -> Dict[str, float]:
        """
        Analyze a single review for sentiment
        Returns scores for different aspects
        """
        if not review_text or not self.pipeline:
            return {}
        
        try:
            # Overall sentiment
            result = self.pipeline(review_text[:512])[0]  # Truncate to model limit
            
            # Extract aspect-based sentiments using keyword matching
            aspects = self._extract_aspect_sentiments(review_text)
            
            return {
                'overall_sentiment': result['label'],
                'overall_score': result['score'],
                **aspects
            }
        
        except Exception as e:
            logger.error(f"Error analyzing review: {e}")
            return {}
    
    def _extract_aspect_sentiments(self, text: str) -> Dict[str, float]:
        """
        Extract sentiment for specific aspects using keyword-based approach
        Aspects: teaching_clarity, grading_fairness, engagement, accessibility, class_difficulty
        """
        text_lower = text.lower()
        aspects = {}
        
        # Teaching clarity keywords
        clarity_keywords = ['clear', 'explain', 'understand', 'confusing', 'organized']
        aspects['teaching_clarity'] = self._score_aspect(text_lower, clarity_keywords)
        
        # Grading fairness keywords
        grading_keywords = ['fair', 'grade', 'exam', 'test', 'harsh', 'easy grader']
        aspects['grading_fairness'] = self._score_aspect(text_lower, grading_keywords)
        
        # Engagement keywords
        engagement_keywords = ['engaging', 'interesting', 'boring', 'passionate', 'enthusiastic']
        aspects['engagement'] = self._score_aspect(text_lower, engagement_keywords)
        
        # Accessibility keywords
        accessibility_keywords = ['helpful', 'available', 'office hours', 'responsive', 'approachable']
        aspects['accessibility'] = self._score_aspect(text_lower, accessibility_keywords)
        
        # Class difficulty keywords
        difficulty_keywords = ['difficult', 'hard', 'easy', 'challenging', 'workload']
        aspects['class_difficulty'] = self._score_aspect(text_lower, difficulty_keywords)
        
        return aspects
    
    def _score_aspect(self, text: str, keywords: List[str]) -> float:
        """
        Score an aspect based on keyword presence
        Returns a score from 0 to 1
        """
        positive_words = ['good', 'great', 'excellent', 'amazing', 'helpful', 'clear', 'fair']
        negative_words = ['bad', 'terrible', 'awful', 'poor', 'confusing', 'unfair', 'harsh']
        
        score = 0.5  # Neutral default
        
        for keyword in keywords:
            if keyword in text:
                # Check surrounding context for sentiment
                keyword_index = text.find(keyword)
                context = text[max(0, keyword_index-50):min(len(text), keyword_index+50)]
                
                # Simple sentiment scoring
                if any(pos in context for pos in positive_words):
                    score += 0.1
                elif any(neg in context for neg in negative_words):
                    score -= 0.1
        
        return max(0.0, min(1.0, score))  # Clamp to [0, 1]
    
    def analyze_reviews_batch(self, reviews: List[str]) -> List[Dict[str, float]]:
        """Analyze multiple reviews in batch"""
        return [self.analyze_review(review) for review in reviews]
    
    def generate_professor_metrics(
        self,
        reviews: List[Dict[str, any]]
    ) -> Dict[str, float]:
        """
        Generate aggregate metrics from analyzed reviews
        """
        if not reviews:
            return {}
        
        # Analyze all review comments
        sentiments = []
        for review in reviews:
            if 'comment' in review and review['comment']:
                sentiment = self.analyze_review(review['comment'])
                sentiments.append(sentiment)
        
        if not sentiments:
            return {}
        
        # Calculate averages
        aspects = ['teaching_clarity', 'grading_fairness', 'engagement', 'accessibility', 'class_difficulty']
        metrics = {}
        
        for aspect in aspects:
            scores = [s.get(aspect, 0) for s in sentiments if aspect in s]
            if scores:
                metrics[f'{aspect}_score'] = sum(scores) / len(scores) * 100  # Convert to 0-100
        
        return metrics
    
    def calculate_composite_score(self, metrics: Dict[str, float]) -> int:
        """
        Calculate a composite score (0-100) from aspect metrics
        Weighted average of different aspects
        """
        weights = {
            'teaching_clarity_score': 0.30,
            'grading_fairness_score': 0.20,
            'engagement_score': 0.25,
            'accessibility_score': 0.15,
            'class_difficulty_score': 0.10
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for aspect, weight in weights.items():
            if aspect in metrics:
                weighted_sum += metrics[aspect] * weight
                total_weight += weight
        
        if total_weight == 0:
            return 50  # Default neutral score
        
        return int(weighted_sum / total_weight)
    
    def score_to_grade(self, score: int) -> str:
        """Convert composite score to letter grade"""
        if score >= 93:
            return 'A'
        elif score >= 90:
            return 'A-'
        elif score >= 87:
            return 'B+'
        elif score >= 83:
            return 'B'
        elif score >= 80:
            return 'B-'
        elif score >= 77:
            return 'C+'
        elif score >= 73:
            return 'C'
        elif score >= 70:
            return 'C-'
        elif score >= 67:
            return 'D+'
        elif score >= 60:
            return 'D'
        else:
            return 'F'


# Singleton instance
sentiment_analyzer = SentimentAnalyzer()
