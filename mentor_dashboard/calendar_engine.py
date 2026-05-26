"""Calendar engine for calculating expected hours based on semester calendar."""

import typing as t
from datetime import datetime, timedelta

from .config_loader import SemesterConfig


def get_week_start(date: datetime) -> datetime:
    """Get Monday of the week containing the given date.
    
    Args:
        date: Any date in the week
        
    Returns:
        datetime object for the Monday of that week
    """
    # weekday() returns 0 for Monday, 6 for Sunday
    days_since_monday = date.weekday()
    monday = date - timedelta(days=days_since_monday)
    # Return at midnight
    return datetime(monday.year, monday.month, monday.day)


def _get_closest_saturday(date: datetime) -> datetime:
    """Get the Saturday closest to the given date.
    
    Args:
        date: The reference date
        
    Returns:
        datetime object for the closest Saturday
    """
    # weekday(): Monday=0, ..., Saturday=5, Sunday=6
    days_to_saturday = (5 - date.weekday()) % 7
    days_from_prev_saturday = (date.weekday() - 5) % 7
    
    if days_to_saturday == 0:
        # It's Saturday
        return date
    elif days_to_saturday <= days_from_prev_saturday:
        # Next Saturday is closer
        return date + timedelta(days=days_to_saturday)
    else:
        # Previous Saturday is closer
        return date - timedelta(days=days_from_prev_saturday)


def _get_closest_sunday(date: datetime) -> datetime:
    """Get the Sunday closest to the given date.
    
    Args:
        date: The reference date
        
    Returns:
        datetime object for the closest Sunday
    """
    # weekday(): Monday=0, ..., Saturday=5, Sunday=6
    days_to_sunday = (6 - date.weekday()) % 7
    days_from_prev_sunday = (date.weekday() + 1) % 7
    
    if days_to_sunday == 0:
        # It's Sunday
        return date
    elif days_to_sunday <= days_from_prev_sunday:
        # Next Sunday is closer
        return date + timedelta(days=days_to_sunday)
    else:
        # Previous Sunday is closer
        return date - timedelta(days=days_from_prev_sunday)


def is_break_week(week_start: datetime, semester: SemesterConfig) -> bool:
    """Determine if the given week is a break week.
    
    Break weeks span from Saturday closest to break start through
    Sunday closest to break end. No work is expected during break weeks
    (though students may work to make up time).
    
    Args:
        week_start: Monday of the week to check
        semester: Semester configuration with break information
        
    Returns:
        True if this week is during the break period
    """
    if not semester.break_period:
        return False
    
    # Get break boundaries
    break_saturday = _get_closest_saturday(semester.break_period.start)
    break_sunday = _get_closest_sunday(semester.break_period.end)
    
    # Check if the week overlaps with the break period
    # Week is Mon-Sun, so week_end is Sunday
    week_end = week_start + timedelta(days=6)
    
    # Week is a break week if it overlaps with [break_saturday, break_sunday]
    return not (week_end < break_saturday or week_start > break_sunday)


def count_holidays_in_week(week_start: datetime, semester: SemesterConfig) -> int:
    """Count the number of weekday holidays (Mon-Fri) in the given week.
    
    Args:
        week_start: Monday of the week to check
        semester: Semester configuration with holiday information
        
    Returns:
        Number of weekday holidays in the week (0-5)
    """
    if not semester.holidays:
        return 0
    
    count = 0
    for holiday in semester.holidays:
        # Check if holiday falls in this week
        if week_start <= holiday.date < week_start + timedelta(days=7):
            # Check if it's a weekday (Mon-Fri)
            if holiday.date.weekday() < 5:  # 0-4 are Mon-Fri
                count += 1
    
    return count


def calculate_expected_hours_for_week(
    week_start: datetime,
    semester: SemesterConfig
) -> float:
    """Calculate expected hours for a specific week.
    
    Rules:
    - Break week: 0 hours expected (but students may work to make up time)
    - Regular week with holidays: base_hours - (base_hours / 5 * num_holidays)
    - Regular week: base_hours from config
    
    Args:
        week_start: Monday of the week
        semester: Semester configuration
        
    Returns:
        Expected hours for the week
    """
    # Check if it's a break week
    if is_break_week(week_start, semester):
        return 0.0
    
    # Get base expected hours
    base_hours = semester.hours
    
    # Count holidays in the week
    num_holidays = count_holidays_in_week(week_start, semester)
    
    # Calculate adjusted hours
    # Each holiday reduces expected hours by 1/5 of the weekly total
    hours_per_day = base_hours / 5.0
    adjusted_hours = base_hours - (hours_per_day * num_holidays)
    
    return max(0.0, adjusted_hours)  # Ensure non-negative


def get_weeks_in_semester(semester: SemesterConfig) -> list[datetime]:
    """Return list of week start dates (Mondays) in the semester.
    
    Args:
        semester: Semester configuration
        
    Returns:
        List of datetime objects representing the Monday of each week
    """
    weeks = []
    
    # Start from the Monday of the first week
    current_week = get_week_start(semester.start_date)
    
    # End at the Monday of the last week
    end_week = get_week_start(semester.end_date)
    
    while current_week <= end_week:
        weeks.append(current_week)
        current_week += timedelta(days=7)
    
    return weeks


def get_expected_hours_map(semester: SemesterConfig) -> dict[datetime, float]:
    """Get a mapping of week start dates to expected hours.
    
    This is a convenience function that combines get_weeks_in_semester
    and calculate_expected_hours_for_week.
    
    Args:
        semester: Semester configuration
        
    Returns:
        Dictionary mapping week start dates to expected hours
    """
    weeks = get_weeks_in_semester(semester)
    return {
        week: calculate_expected_hours_for_week(week, semester)
        for week in weeks
    }
