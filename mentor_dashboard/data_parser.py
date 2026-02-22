"""Parse and validate CSV time tracking data."""

import re
import typing as t
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dateutil.parser import parse as parse_date

from .name_resolver import NameResolver


@dataclass
class TimeEntry:
    """Represents a single time tracking entry."""
    project: str
    user: str
    group: str
    start_date: datetime
    end_date: datetime
    duration_hours: float
    activity: str
    category: str
    description: str
    
    @property
    def week_start(self) -> datetime:
        """Get the Monday of the week this entry belongs to."""
        # Calculate days since Monday (0=Monday, 6=Sunday)
        days_since_monday = self.start_date.weekday()
        monday = self.start_date - timedelta(days=days_since_monday)
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def extract_activity_category(tags: str) -> tuple[str, str]:
    """Extract activity and category from tags string.
    
    Args:
        tags: String like "ACTIVITY: Learning and Evaluation, CATEGORY: Academic"
        
    Returns:
        tuple of (activity, category), defaulting to "Uncategorized" if not found
    """
    if pd.isna(tags) or not tags.strip():
        return "Uncategorized", "Uncategorized"
    
    activity = "Uncategorized"
    category = "Uncategorized"
    
    # Extract ACTIVITY
    activity_match = re.search(r'ACTIVITY:\s*([^,\n]+)', tags, re.IGNORECASE)
    if activity_match:
        activity = activity_match.group(1).strip()
    
    # Extract CATEGORY  
    category_match = re.search(r'CATEGORY:\s*([^,\n]+)', tags, re.IGNORECASE)
    if category_match:
        category = category_match.group(1).strip()
    
    return activity, category


def parse_csv_file(file_path: Path, name_resolver: t.Optional[NameResolver] = None) -> list[TimeEntry]:
    """Parse CSV file and return list of TimeEntry objects.
    
    Args:
        file_path: Path to CSV file
        name_resolver: Optional name resolver to convert Andrew IDs to proper names
        
    Returns:
        List of TimeEntry objects
        
    Raises:
        ValueError: If required columns are missing or data is invalid
    """
    try:
        # Read CSV with proper handling for quoted strings containing commas
        df = pd.read_csv(file_path, encoding='utf-8')
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")
    
    # Check required columns (Email is optional for name resolution)
    required_columns = ['Project', 'User', 'Group', 'Start Date', 'End Date', 
                       'Duration (decimal)', 'Tags']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    entries: list[TimeEntry] = []
    
    for idx, row in df.iterrows():
        try:
            # Parse dates - handle different formats
            start_date = parse_date(row['Start Date'], dayfirst=True)
            end_date = parse_date(row['End Date'], dayfirst=True)
            
            # Extract activity and category from tags
            activity, category = extract_activity_category(row.get('Tags', ''))
            
            # Handle missing values
            project = str(row.get('Project', 'Unknown')).strip()
            user_raw = str(row.get('User', 'Unknown')).strip()
            
            # Resolve user name if name resolver is provided
            if name_resolver:
                email_field = str(row.get('Email', ''))
                user = name_resolver.resolve_name(user_raw, email_field)
            else:
                user = user_raw
            
            group_raw = row.get('Group', 'Unknown')
            # Handle pandas NaN values
            if pd.isna(group_raw) or str(group_raw).lower() == 'nan':
                group = 'Unknown'
            else:
                group = str(group_raw).strip()
            duration = float(row.get('Duration (decimal)', 0))
            description = str(row.get('Description', '')).strip()
            
            # Skip entries with zero duration
            if duration <= 0:
                continue
                
            entry = TimeEntry(
                project=project,
                user=user,
                group=group,
                start_date=start_date,
                end_date=end_date,
                duration_hours=duration,
                activity=activity,
                category=category,
                description=description
            )
            entries.append(entry)
            
        except Exception as e:
            print(f"Warning: Skipping row {idx + 1} due to error: {e}")
            continue
    
    if not entries:
        raise ValueError("No valid time entries found in CSV file")
    
    return entries


def group_entries_by_team_and_week(entries: list[TimeEntry]) -> dict[str, dict[datetime, list[TimeEntry]]]:
    """Group time entries by team and week.
    
    Args:
        entries: List of TimeEntry objects
        
    Returns:
        Dictionary with structure: {team_name: {week_start_date: [entries]}}
    """
    grouped: dict[str, dict[datetime, list[TimeEntry]]] = {}
    
    for entry in entries:
        team = entry.group
        week_start = entry.week_start
        
        if team not in grouped:
            grouped[team] = {}
        
        if week_start not in grouped[team]:
            grouped[team][week_start] = []
            
        grouped[team][week_start].append(entry)
    
    return grouped


def get_week_summary(entries: list[TimeEntry]) -> dict[str, t.Any]:
    """Generate summary statistics for a week's entries.
    
    Args:
        entries: List of TimeEntry objects for a single week
        
    Returns:
        Dictionary with summary statistics
    """
    if not entries:
        return {
            'total_hours': 0,
            'num_participants': 0,
            'avg_hours_per_person': 0,
            'activities': {},
            'categories': {},
            'users': {}
        }
    
    # Calculate totals by different dimensions
    activities: dict[str, float] = {}
    categories: dict[str, float] = {}
    users: dict[str, float] = {}
    
    for entry in entries:
        # Aggregate by activity
        activities[entry.activity] = activities.get(entry.activity, 0) + entry.duration_hours
        
        # Aggregate by category
        categories[entry.category] = categories.get(entry.category, 0) + entry.duration_hours
        
        # Aggregate by user
        users[entry.user] = users.get(entry.user, 0) + entry.duration_hours
    
    total_hours = sum(users.values())
    num_participants = len(users)
    avg_hours = total_hours / num_participants if num_participants > 0 else 0
    
    return {
        'total_hours': total_hours,
        'num_participants': num_participants,
        'avg_hours_per_person': avg_hours,
        'activities': activities,
        'categories': categories,
        'users': users
    }