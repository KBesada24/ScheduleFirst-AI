"""
Schedule optimization engine using constraint satisfaction
"""
import asyncio
from typing import List, Dict, Optional, Set, Tuple
from datetime import time, datetime
from uuid import UUID
import itertools

from ..models.schedule import (
    ScheduleConstraints,
    OptimizedSchedule,
    ScheduleSlot,
    ScheduleConflict
)
from ..models.course import CourseSection
from ..services.supabase_service import supabase_service
from ..utils.logger import get_logger
from ..config import settings


logger = get_logger(__name__)


class ScheduleOptimizer:
    """Optimize course schedules based on constraints"""
    
    def __init__(self):
        self.db = supabase_service
        logger.info("Schedule Optimizer initialized")
    
    async def generate_optimized_schedules(
        self,
        required_courses: List[str],
        semester: str,
        university: str,
        constraints: ScheduleConstraints,
        max_results: int = 5
    ) -> List[OptimizedSchedule]:
        """
        Generate optimized schedules based on requirements and constraints
        """
        logger.info(f"Generating schedules for {len(required_courses)} courses")
        
        # Get all available sections for required courses
        sections_by_course = {}
        
        for course_code in required_courses:
            course = await self.db.get_course_by_code(course_code, semester, university)
            if course:
                sections = await self.db.get_sections_by_course(course.id)
                sections_by_course[course_code] = {
                    'course': course,
                    'sections': sections
                }
        
        if not sections_by_course:
            logger.warning("No sections found for required courses")
            return []
        
        # Generate all possible schedule combinations
        possible_schedules = self._generate_combinations(sections_by_course)
        
        logger.info(f"Generated {len(possible_schedules)} possible combinations")
        
        # Filter and score schedules
        valid_schedules = []
        
        for schedule_sections in possible_schedules:
            # Check constraints
            conflicts = self.detect_conflicts(schedule_sections)
            
            # Filter out schedules with critical conflicts
            if not any(c.severity == 'critical' for c in conflicts):
                # Score the schedule
                schedule = await self._create_scored_schedule(
                    schedule_sections,
                    conflicts,
                    constraints
                )
                valid_schedules.append(schedule)
        
        # Sort by overall score
        valid_schedules.sort(key=lambda s: s.overall_score, reverse=True)
        
        # Assign ranks
        for i, schedule in enumerate(valid_schedules[:max_results], 1):
            schedule.rank = i
        
        logger.info(f"Returning {min(len(valid_schedules), max_results)} optimized schedules")
        return valid_schedules[:max_results]
    
    def _generate_combinations(
        self,
        sections_by_course: Dict[str, Dict]
    ) -> List[List[CourseSection]]:
        """Generate all possible combinations of sections"""
        courses = list(sections_by_course.keys())
        section_lists = [sections_by_course[c]['sections'] for c in courses]
        
        # Generate cartesian product of all section combinations
        combinations = list(itertools.product(*section_lists))
        
        return combinations
    
    async def _create_scored_schedule(
        self,
        sections: List[CourseSection],
        conflicts: List[ScheduleConflict],
        constraints: ScheduleConstraints
    ) -> OptimizedSchedule:
        """Create a scored schedule from sections"""
        slots = []
        total_credits = 0
        professor_ratings = []
        
        for section in sections:
            # Get course info
            course = await self.db.get_course_by_code(
                section.course_id,  # This would need course_code
                constraints.required_course_codes[0],  # Semester from first course
                ""  # University
            )
            
            slot = ScheduleSlot(
                section=section,
                course_code=course.course_code if course else "",
                course_name=course.name if course else "",
                professor_name=section.professor_name,
                professor_grade=None  # TODO: Fetch from DB
            )
            slots.append(slot)
            
            if course:
                total_credits += course.credits or 0
            
            # Get professor rating if available
            if section.professor_name:
                # TODO: Fetch professor rating
                professor_ratings.append(4.0)  # Placeholder
        
        # Calculate scores
        preference_score = self._calculate_preference_score(sections, constraints)
        professor_quality_score = sum(professor_ratings) / len(professor_ratings) * 20 if professor_ratings else 50
        time_convenience_score = self._calculate_time_convenience_score(sections, constraints)
        
        # Overall score (weighted average)
        overall_score = (
            preference_score * 0.3 +
            professor_quality_score * 0.4 +
            time_convenience_score * 0.3
        )
        
        avg_rating = sum(professor_ratings) / len(professor_ratings) if professor_ratings else None
        
        return OptimizedSchedule(
            slots=slots,
            total_credits=total_credits,
            average_professor_rating=avg_rating,
            conflicts=conflicts,
            preference_score=preference_score,
            professor_quality_score=professor_quality_score,
            time_convenience_score=time_convenience_score,
            overall_score=overall_score
        )
    
    def detect_conflicts(self, sections: List[CourseSection]) -> List[ScheduleConflict]:
        """Detect scheduling conflicts between sections"""
        conflicts = []
        
        for i, section1 in enumerate(sections):
            for section2 in sections[i+1:]:
                # Check time overlap
                if self._has_time_overlap(section1, section2):
                    conflicts.append(ScheduleConflict(
                        conflict_type="time_overlap",
                        section1_id=section1.id,
                        section2_id=section2.id,
                        description=f"Time conflict between sections",
                        severity="critical",
                        suggestion="Choose different sections"
                    ))
                
                # Check travel time between campuses
                if self._has_travel_conflict(section1, section2):
                    conflicts.append(ScheduleConflict(
                        conflict_type="travel_time",
                        section1_id=section1.id,
                        section2_id=section2.id,
                        description="Insufficient time to travel between campuses",
                        severity="warning",
                        suggestion="Allow more time between classes"
                    ))
        
        return conflicts
    
    def _has_time_overlap(self, section1: CourseSection, section2: CourseSection) -> bool:
        """Check if two sections have overlapping times"""
        if not all([section1.days, section1.start_time, section1.end_time,
                    section2.days, section2.start_time, section2.end_time]):
            return False
        
        # Check if they share any days
        days1 = set(section1.days.replace('Th', 'R'))  # Normalize Thursday
        days2 = set(section2.days.replace('Th', 'R'))
        
        if not days1.intersection(days2):
            return False
        
        # Check time overlap
        return (section1.start_time < section2.end_time and 
                section1.end_time > section2.start_time)
    
    def _has_travel_conflict(self, section1: CourseSection, section2: CourseSection) -> bool:
        """Check if there's insufficient travel time between sections"""
        if not all([section1.end_time, section2.start_time, section1.location, section2.location]):
            return False
        
        # If different campuses, check if there's at least 30 minutes between classes
        if section1.location != section2.location:
            time_diff = datetime.combine(datetime.min, section2.start_time) - \
                       datetime.combine(datetime.min, section1.end_time)
            return time_diff.total_seconds() < 1800  # 30 minutes
        
        return False
    
    def _calculate_preference_score(
        self,
        sections: List[CourseSection],
        constraints: ScheduleConstraints
    ) -> float:
        """Calculate how well schedule matches user preferences"""
        score = 100.0
        
        # Check time preferences
        if constraints.earliest_start_time:
            earliest = time.fromisoformat(constraints.earliest_start_time)
            for section in sections:
                if section.start_time and section.start_time < earliest:
                    score -= 10
        
        if constraints.latest_end_time:
            latest = time.fromisoformat(constraints.latest_end_time)
            for section in sections:
                if section.end_time and section.end_time > latest:
                    score -= 10
        
        # Check day preferences
        if constraints.preferred_days:
            for section in sections:
                if section.days and section.days not in constraints.preferred_days:
                    score -= 5
        
        # Check online preference
        if not constraints.allow_online:
            for section in sections:
                if section.modality and 'online' in section.modality.lower():
                    score -= 15
        
        return max(0.0, score)
    
    def _calculate_time_convenience_score(
        self,
        sections: List[CourseSection],
        constraints: ScheduleConstraints
    ) -> float:
        """Calculate convenience score based on time distribution"""
        score = 100.0
        
        # Penalize too many classes on one day
        days_dict: Dict[str, int] = {}
        for section in sections:
            if section.days:
                for day in section.days:
                    days_dict[day] = days_dict.get(day, 0) + 1
        
        for count in days_dict.values():
            if count > 3:
                score -= 10 * (count - 3)
        
        # Reward balanced distribution
        if len(days_dict) >= 3:
            score += 10
        
        return max(0.0, score)


# Singleton instance
schedule_optimizer = ScheduleOptimizer()
