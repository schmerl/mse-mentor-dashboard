"""Generate weekly reports with charts and trend analysis."""

import typing as t
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .data_parser import TimeEntry, group_entries_by_team_and_week, get_week_summary
from .charts import (
    create_individual_charts, create_team_charts, create_trend_indicator,
    figure_to_bytes
)


@dataclass
class WeeklyReport:
    """Represents a weekly report for a team."""
    team: str
    week_start: datetime
    week_end: datetime
    total_hours: float
    num_participants: int
    avg_hours_per_person: float
    individual_summaries: dict[str, dict[str, t.Any]]
    team_activities: dict[str, float]
    team_categories: dict[str, float]
    activity_trends: dict[str, str]
    category_trends: dict[str, str]
    

def format_week_range(week_start: datetime) -> str:
    """Format week range as string.
    
    Args:
        week_start: Monday of the week
        
    Returns:
        Formatted string like "January 13-19, 2026"
    """
    week_end = week_start + timedelta(days=6)
    
    if week_start.month == week_end.month:
        return f"{week_start.strftime('%B %d')}-{week_end.strftime('%d, %Y')}"
    else:
        return f"{week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}"


def calculate_user_time_trends(user_weekly_hours: list[float]) -> str:
    """Calculate time trend for a user based on recent weeks.
    
    Args:
        user_weekly_hours: List of weekly hours for user (chronological order)
        
    Returns:
        Trend indicator string
    """
    if len(user_weekly_hours) < 2:
        return '★'  # New or insufficient data
    
    # Use last 3-4 weeks if available, otherwise last 2 weeks
    recent_weeks = user_weekly_hours[-min(4, len(user_weekly_hours)):]
    
    if len(recent_weeks) == 2:
        # Simple comparison
        current = recent_weeks[-1]
        previous = recent_weeks[-2]
        if previous == 0:
            return '★' if current > 0 else '→'
        change_percent = (current - previous) / previous * 100
    else:
        # Calculate trend over multiple weeks
        # Simple linear trend: compare first half to second half
        mid_point = len(recent_weeks) // 2
        first_half_avg = sum(recent_weeks[:mid_point]) / mid_point if mid_point > 0 else 0
        second_half_avg = sum(recent_weeks[mid_point:]) / (len(recent_weeks) - mid_point)
        
        if first_half_avg == 0:
            return '★' if second_half_avg > 0 else '→'
        change_percent = (second_half_avg - first_half_avg) / first_half_avg * 100
    
    if change_percent > 10:  # More than 10% increase trend
        return '↑'
    elif change_percent < -10:  # More than 10% decrease trend
        return '↓'
    else:
        return '→'


def get_hours_status_color(actual_hours: float, expected_hours: float) -> tuple[str, str]:
    """Get color and status for student hours based on expected hours.
    
    Args:
        actual_hours: Hours actually logged
        expected_hours: Expected hours per week
        
    Returns:
        Tuple of (color_hex, status_text)
    """
    if expected_hours <= 0:
        return '#000000', 'Normal'  # Black text if no expectation set
    
    percentage = (actual_hours / expected_hours) * 100
    
    if percentage < 70:  # More than 30% below
        return '#CC0000', f'Significantly Below Expected ({percentage:.0f}%)'  # Red
    elif percentage < 85:  # 15-30% below
        return '#FF8800', f'Below Expected ({percentage:.0f}%)'  # Orange
    elif percentage > 130:  # More than 30% above
        return '#CC0000', f'Significantly Above Expected ({percentage:.0f}%)'  # Red
    elif percentage > 115:  # 15-30% above
        return '#FF8800', f'Above Expected ({percentage:.0f}%)'  # Orange
    else:
        return '#006600', f'Meeting Expectations ({percentage:.0f}%)'  # Green


def calculate_trends(current_week: dict[str, float], previous_week: dict[str, float]) -> dict[str, str]:
    """Calculate trend indicators for activities/categories.
    
    Args:
        current_week: Current week's data (activity/category -> hours)
        previous_week: Previous week's data (activity/category -> hours)
        
    Returns:
        Dictionary mapping activity/category names to trend indicators
    """
    trends: dict[str, str] = {}
    
    # Get all activities/categories from both weeks
    all_items = set(current_week.keys()) | set(previous_week.keys())
    
    for item in all_items:
        current_value = current_week.get(item, 0)
        previous_value = previous_week.get(item, 0)
        is_new = item not in previous_week
        
        trends[item] = create_trend_indicator(current_value, previous_value, is_new)
    
    return trends


def generate_weekly_reports(entries: list[TimeEntry]) -> list[WeeklyReport]:
    """Generate weekly reports for all teams and weeks.
    
    Args:
        entries: List of all time entries
        
    Returns:
        List of WeeklyReport objects sorted by team and week
    """
    # Group entries by team and week
    grouped_data = group_entries_by_team_and_week(entries)
    
    reports: list[WeeklyReport] = []
    
    for team, weeks_data in grouped_data.items():
        # Sort weeks in reverse chronological order (most recent first)
        sorted_weeks = sorted(weeks_data.keys(), reverse=True)
        
        # For trend calculations, we need to process weeks chronologically
        # but display them in reverse chronological order
        weeks_for_trends = sorted(weeks_data.keys())  # Chronological for trend calculation
        week_trends: dict[datetime, tuple[dict[str, str], dict[str, str]]] = {}
        
        previous_week_activities: dict[str, float] = {}
        previous_week_categories: dict[str, float] = {}
        
        # First pass: calculate trends chronologically
        for week_start in weeks_for_trends:
            week_entries = weeks_data[week_start]
            week_summary = get_week_summary(week_entries)
            
            # Calculate trends
            activity_trends = calculate_trends(
                week_summary['activities'], 
                previous_week_activities
            )
            category_trends = calculate_trends(
                week_summary['categories'],
                previous_week_categories
            )
            
            # Store trends for this week
            week_trends[week_start] = (activity_trends, category_trends)
            
            # Store current week data for next iteration's trend calculation
            previous_week_activities = week_summary['activities'].copy()
            previous_week_categories = week_summary['categories'].copy()
        
        # Second pass: generate reports in reverse chronological order
        for week_start in sorted_weeks:
            week_entries = weeks_data[week_start]
            week_summary = get_week_summary(week_entries)
            
            # Get pre-calculated trends
            activity_trends, category_trends = week_trends[week_start]
            
            # Generate individual summaries
            individual_summaries: dict[str, dict[str, t.Any]] = {}
            
            # Group entries by user for this week
            user_entries: dict[str, list[TimeEntry]] = {}
            for entry in week_entries:
                if entry.user not in user_entries:
                    user_entries[entry.user] = []
                user_entries[entry.user].append(entry)
            
            # Create individual summaries
            for user, user_week_entries in user_entries.items():
                user_summary = get_week_summary(user_week_entries)
                individual_summaries[user] = user_summary
            
            # Create weekly report
            report = WeeklyReport(
                team=team,
                week_start=week_start,
                week_end=week_start + timedelta(days=6),
                total_hours=week_summary['total_hours'],
                num_participants=week_summary['num_participants'],
                avg_hours_per_person=week_summary['avg_hours_per_person'],
                individual_summaries=individual_summaries,
                team_activities=week_summary['activities'],
                team_categories=week_summary['categories'],
                activity_trends=activity_trends,
                category_trends=category_trends
            )
            
            reports.append(report)
    
    # Sort reports by team name and then by week (most recent first)
    reports.sort(key=lambda r: (r.team, -r.week_start.timestamp()))
    return reports


def generate_user_charts_for_week(entries: list[TimeEntry]) -> dict[str, tuple[bytes, bytes]]:
    """Generate individual user charts for a week.
    
    Args:
        entries: List of time entries for a single week
        
    Returns:
        Dictionary mapping usernames to (category_chart_bytes, activity_chart_bytes)
    """
    user_charts: dict[str, tuple[bytes, bytes]] = {}
    
    # Group entries by user
    user_entries: dict[str, list[TimeEntry]] = {}
    for entry in entries:
        if entry.user not in user_entries:
            user_entries[entry.user] = []
        user_entries[entry.user].append(entry)
    
    # Generate charts for each user
    for user, user_week_entries in user_entries.items():
        category_chart, activity_chart = create_individual_charts(user_week_entries, user)
        
        # Convert to bytes for PDF embedding
        category_bytes = figure_to_bytes(category_chart).getvalue()
        activity_bytes = figure_to_bytes(activity_chart).getvalue()
        
        user_charts[user] = (category_bytes, activity_bytes)
    
    return user_charts


def generate_team_charts_for_week(entries: list[TimeEntry], team: str) -> tuple[bytes, bytes]:
    """Generate team charts for a week.
    
    Args:
        entries: List of time entries for a single week and team
        team: Team name
        
    Returns:
        Tuple of (category_chart_bytes, activity_chart_bytes)
    """
    category_chart, activity_chart = create_team_charts(entries, team)
    
    # Convert to bytes for PDF embedding
    category_bytes = figure_to_bytes(category_chart).getvalue()
    activity_bytes = figure_to_bytes(activity_chart).getvalue()
    
    return category_bytes, activity_bytes


def get_user_historical_data(entries: list[TimeEntry], user: str, team: str) -> dict:
    """Get historical weekly data for a user and team/global averages.
    
    Args:
        entries: All time entries
        user: Username to get data for
        team: Team name the user belongs to
        
    Returns:
        Dict with user_weekly, team_avg_weekly, all_teams_avg_weekly data
    """
    # Group all entries by team and week
    grouped_data = group_entries_by_team_and_week(entries)
    
    # Get user's weekly data
    user_weekly = {}
    if team in grouped_data:
        for week_start, week_entries in grouped_data[team].items():
            user_week_hours = sum(
                entry.duration_hours for entry in week_entries 
                if entry.user == user
            )
            if user_week_hours > 0:  # Only include weeks where user logged time
                user_weekly[week_start] = user_week_hours
    
    # Get team average data (excluding the current user for fair comparison)
    team_avg_weekly = {}
    if team in grouped_data:
        for week_start, week_entries in grouped_data[team].items():
            # Get all users in team for this week (excluding current user)
            team_users_hours = {}
            for entry in week_entries:
                if entry.user != user:  # Exclude current user
                    if entry.user not in team_users_hours:
                        team_users_hours[entry.user] = 0
                    team_users_hours[entry.user] += entry.duration_hours
            
            if team_users_hours:
                team_avg_weekly[week_start] = sum(team_users_hours.values()) / len(team_users_hours)
    
    # Get all teams average data
    all_teams_avg_weekly = {}
    all_weeks = set()
    for team_data in grouped_data.values():
        all_weeks.update(team_data.keys())
    
    for week_start in all_weeks:
        week_user_hours = {}
        for team_name, team_weeks in grouped_data.items():
            if week_start in team_weeks:
                for entry in team_weeks[week_start]:
                    if entry.user not in week_user_hours:
                        week_user_hours[entry.user] = 0
                    week_user_hours[entry.user] += entry.duration_hours
        
        if week_user_hours:
            all_teams_avg_weekly[week_start] = sum(week_user_hours.values()) / len(week_user_hours)
    
    return {
        'user_weekly': user_weekly,
        'team_avg_weekly': team_avg_weekly,
        'all_teams_avg_weekly': all_teams_avg_weekly
    }


def get_all_teams_historical_data(entries: list[TimeEntry]) -> dict:
    """Get historical weekly data for all teams.
    
    Args:
        entries: All time entries
        
    Returns:
        Dict mapping team_name -> {week_start -> total_hours}
    """
    grouped_data = group_entries_by_team_and_week(entries)
    
    all_teams_weekly = {}
    for team_name, team_weeks in grouped_data.items():
        all_teams_weekly[team_name] = {}
        for week_start, week_entries in team_weeks.items():
            total_hours = sum(entry.duration_hours for entry in week_entries)
            all_teams_weekly[team_name][week_start] = total_hours
    
    return all_teams_weekly
