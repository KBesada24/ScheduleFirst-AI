"""
Sentiment analysis service for professor reviews
Uses Ollama API for aspect-based sentiment analysis
"""
from typing import List, Dict, Optional, Any, Union
import json
from ollama import Client as OllamaClient

from ..config import settings
from ..utils.logger import get_logger


logger = get_logger(__name__)


class SentimentAnalyzer:
    """Analyze sentiment in professor reviews using Ollama AI"""
    
    def __init__(self):
        headers = {}
        if settings.ollama_api_key:
            headers['Authorization'] = f'Bearer {settings.ollama_api_key}'
        self.client = OllamaClient(host=settings.ollama_host, headers=headers)
        self.model = settings.ollama_model
        logger.info("Sentiment analyzer initialized with Ollama API")
    
    def analyze_review(self, review_text: str) -> Dict[str, Union[str, float]]:
        """
        Analyze a single review for sentiment using Ollama
        Returns scores for different aspects
        """
        if not review_text:
            return {}
        
        try:
            prompt = f"""Analyze this professor review and return ONLY a JSON object with sentiment scores (0-100):

Review: "{review_text}"

Return this exact format:
{{
    "overall_sentiment": "POSITIVE/NEGATIVE/NEUTRAL",
    "overall_score": 0-100,
    "teaching_clarity": 0-100,
    "grading_fairness": 0-100,
    "engagement": 0-100,
    "accessibility": 0-100,
    "class_difficulty": 0-100
}}

Rules:
- Higher scores (70-100) = positive sentiment
- Medium scores (40-70) = neutral
- Lower scores (0-40) = negative sentiment
- teaching_clarity: How clear are their explanations
- grading_fairness: How fair is their grading
- engagement: How engaging is the class
- accessibility: How available/helpful is the professor
- class_difficulty: How challenging is the class (higher = harder)"""

            response = self.client.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                format='json',
            )
            
            result_text = response.message.content.strip()
            result = json.loads(result_text)
            
            # Normalize scores to 0-1 range
            normalized = {
                'overall_sentiment': result.get('overall_sentiment', 'NEUTRAL'),
                'overall_score': result.get('overall_score', 50) / 100,
                'teaching_clarity': result.get('teaching_clarity', 50) / 100,
                'grading_fairness': result.get('grading_fairness', 50) / 100,
                'engagement': result.get('engagement', 50) / 100,
                'accessibility': result.get('accessibility', 50) / 100,
                'class_difficulty': result.get('class_difficulty', 50) / 100
            }
            
            return normalized
        
        except Exception as e:
            logger.error(f"Error analyzing review with Ollama: {e}")
            # Fallback to neutral scores
            return {
                'overall_sentiment': 'NEUTRAL',
                'overall_score': 0.5,
                'teaching_clarity': 0.5,
                'grading_fairness': 0.5,
                'engagement': 0.5,
                'accessibility': 0.5,
                'class_difficulty': 0.5
            }
    
    def analyze_reviews_batch(self, reviews: List[str], batch_size: int = 5) -> List[Dict[str, Union[str, float]]]:
        """
        Analyze multiple reviews in batch using Ollama
        Processes in batches to avoid rate limits
        """
        if not reviews:
            return []
        
        results = []
        
        # Process in batches
        for i in range(0, len(reviews), batch_size):
            batch = reviews[i:i+batch_size]
            
            try:
                # Create a batch prompt
                reviews_text = "\n\n".join([f"Review {j+1}: {r}" for j, r in enumerate(batch)])
                
                prompt = f"""Analyze these {len(batch)} professor reviews and return ONLY a JSON object with a "reviews" key containing an array of sentiment scores:

{reviews_text}

Return this exact format:
{{
    "reviews": [
        {{
            "overall_sentiment": "POSITIVE/NEGATIVE/NEUTRAL",
            "overall_score": 0-100,
            "teaching_clarity": 0-100,
            "grading_fairness": 0-100,
            "engagement": 0-100,
            "accessibility": 0-100,
            "class_difficulty": 0-100
        }}
    ]
}}"""

                response = self.client.chat(
                    model=self.model,
                    messages=[{'role': 'user', 'content': prompt}],
                    format='json',
                )
                
                result_text = response.message.content.strip()
                parsed = json.loads(result_text)
                batch_results = parsed.get('reviews', [parsed] if isinstance(parsed, dict) else parsed)
                
                # Normalize scores
                for result in batch_results:
                    normalized = {
                        'overall_sentiment': result.get('overall_sentiment', 'NEUTRAL'),
                        'overall_score': result.get('overall_score', 50) / 100,
                        'teaching_clarity': result.get('teaching_clarity', 50) / 100,
                        'grading_fairness': result.get('grading_fairness', 50) / 100,
                        'engagement': result.get('engagement', 50) / 100,
                        'accessibility': result.get('accessibility', 50) / 100,
                        'class_difficulty': result.get('class_difficulty', 50) / 100
                    }
                    results.append(normalized)
            
            except Exception as e:
                logger.error(f"Error in batch analysis: {e}")
                # Add neutral scores for failed batch
                for _ in batch:
                    results.append({
                        'overall_sentiment': 'NEUTRAL',
                        'overall_score': 0.5,
                        'teaching_clarity': 0.5,
                        'grading_fairness': 0.5,
                        'engagement': 0.5,
                        'accessibility': 0.5,
                        'class_difficulty': 0.5
                    })
        
        return results
    
    def generate_professor_metrics(
        self,
        reviews: List[Dict[str, Any]]
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
            scores = [s.get(aspect, 0.5) for s in sentiments if aspect in s]
            if scores:
                metrics[f'{aspect}_score'] = (sum(scores) / len(scores)) * 100  # Convert to 0-100
        
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
