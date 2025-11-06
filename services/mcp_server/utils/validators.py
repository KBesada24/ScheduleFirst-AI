"""
Input validation utilities
"""
import re
from datetime import time
from typing import Optional, Tuple

from .logger import get_logger


logger = get_logger(__name__)


def validate_course_code(course_code: str) -> bool:
    """
    Validate course code format (e.g., CSC381, MATH201)
    Returns True if valid
    """
    if not course_code:
        return False
    
    # Pattern: 2-4 letters followed by 3-4 digits
    pattern = r'^[A-Z]{2,4}\s?\d{3,4}$'
    return bool(re.match(pattern, course_code.upper()))


def validate_semester(semester: str) -> bool:
    """
    Validate semester format (e.g., "Fall 2025", "Spring 2026")
    Returns True if valid
    """
    if not semester:
        return False
    
    # Pattern: (Fall|Spring|Summer|Winter) YYYY
    pattern = r'^(Fall|Spring|Summer|Winter)\s\d{4}$'
    return bool(re.match(pattern, semester))


def parse_semester(semester: str) -> Optional[Tuple[str, int]]:
    """
    Parse semester string into term and year
    Returns (term, year) or None if invalid
    """
    if not validate_semester(semester):
        return None
    
    parts = semester.split()
    return (parts[0], int(parts[1]))


def validate_time_range(start_time: str, end_time: str) -> bool:
    """
    Validate time range format (HH:MM)
    Returns True if valid and end_time > start_time
    """
    try:
        start = time.fromisoformat(start_time)
        end = time.fromisoformat(end_time)
        return end > start
    except (ValueError, AttributeError):
        return False


def parse_time_string(time_str: str) -> Optional[time]:
    """
    Parse time string to time object
    Supports formats: HH:MM, HH:MM AM/PM
    """
    if not time_str:
        return None
    
    # Try ISO format first (HH:MM)
    try:
        return time.fromisoformat(time_str)
    except ValueError:
        pass
    
    # Try 12-hour format (HH:MM AM/PM)
    try:
        match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_str.upper())
        if match:
            hour, minute, period = match.groups()
            hour = int(hour)
            minute = int(minute)
            
            if period == 'PM' and hour != 12:
                hour += 12
            elif period == 'AM' and hour == 12:
                hour = 0
            
            return time(hour, minute)
    except (ValueError, AttributeError):
        pass
    
    return None


def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_cuny_school(school_name: str) -> bool:
    """Validate CUNY school name"""
    cuny_schools = {
        "City College", "Hunter College", "Queens College", "Baruch College",
        "Brooklyn College", "Lehman College", "York College", "College of Staten Island",
        "John Jay College", "Medgar Evers College", "New York City College of Technology",
        "Borough of Manhattan Community College", "Bronx Community College",
        "Hostos Community College", "Kingsborough Community College",
        "LaGuardia Community College", "Queensborough Community College",
        "Graduate School", "School of Professional Studies", "School of Labor and Urban Studies",
        "Macaulay Honors College", "School of Law", "School of Medicine",
        "School of Public Health", "Craig Newmark Graduate School of Journalism"
    }
    
    return school_name in cuny_schools


def sanitize_string(text: str, max_length: int = 500) -> str:
    """
    Sanitize string input
    - Remove extra whitespace
    - Truncate to max length
    - Remove potentially dangerous characters
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = " ".join(text.split())
    
    # Remove potentially dangerous characters (basic XSS prevention)
    text = re.sub(r'[<>]', '', text)
    
    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text


def validate_days_string(days: str) -> bool:
    """
    Validate days string format (e.g., MWF, TTh, M, Online)
    """
    if not days:
        return False
    
    if days.lower() in ['online', 'tba', 'arranged']:
        return True
    
    # Valid day codes: M, T, W, Th, F, S, Su
    valid_codes = {'M', 'T', 'W', 'Th', 'F', 'S', 'Su'}
    
    # Parse the days string
    i = 0
    while i < len(days):
        if i + 1 < len(days) and days[i:i+2] in valid_codes:
            i += 2
        elif days[i] in valid_codes:
            i += 1
        else:
            return False
    
    return True


def normalize_professor_name(name: str) -> str:
    """
    Normalize professor name for consistent matching
    - Capitalize properly
    - Remove extra whitespace
    - Handle common variations
    """
    if not name:
        return ""
    
    # Basic cleanup
    name = " ".join(name.split())
    
    # Capitalize each word
    name = name.title()
    
    # Handle common suffixes
    name = re.sub(r'\bJr\.?$', 'Jr.', name)
    name = re.sub(r'\bSr\.?$', 'Sr.', name)
    name = re.sub(r'\bIii?$', 'III', name)
    
    return name
