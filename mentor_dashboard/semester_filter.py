"""Filter and group time entries by semester."""

import typing as t

from .config_loader import SemesterConfig
from .data_parser import TimeEntry


def assign_entry_to_semester(
    entry: TimeEntry,
    semesters: list[SemesterConfig]
) -> t.Optional[SemesterConfig]:
    """Determine which semester a time entry belongs to.
    
    Args:
        entry: Time entry to assign
        semesters: List of semester configurations
        
    Returns:
        SemesterConfig that the entry belongs to, or None if no match
    """
    entry_date = entry.start_date
    # Ensure we're comparing dates only
    if hasattr(entry_date, 'date'):
        entry_date = entry_date.date()
    
    for semester in semesters:
        semester_start = semester.start_date.date() if hasattr(semester.start_date, 'date') else semester.start_date
        semester_end = semester.end_date.date() if hasattr(semester.end_date, 'date') else semester.end_date
        
        if semester_start <= entry_date <= semester_end:
            return semester
    
    return None


def group_entries_by_semester(
    entries: list[TimeEntry],
    semesters: list[SemesterConfig]
) -> dict[str, list[TimeEntry]]:
    """Group time entries by semester.
    
    Only includes semesters that have at least one entry.
    
    Args:
        entries: List of all time entries
        semesters: List of semester configurations
        
    Returns:
        Dictionary mapping semester name to list of entries
    """
    semester_entries: dict[str, list[TimeEntry]] = {}
    unassigned: list[TimeEntry] = []
    
    for entry in entries:
        semester = assign_entry_to_semester(entry, semesters)
        if semester:
            if semester.name not in semester_entries:
                semester_entries[semester.name] = []
            semester_entries[semester.name].append(entry)
        else:
            unassigned.append(entry)
    
    # Log warning if there are unassigned entries
    if unassigned:
        dates = [e.start_date.strftime('%Y-%m-%d') for e in unassigned[:5]]
        if len(unassigned) > 5:
            dates.append(f'... and {len(unassigned) - 5} more')
        print(f"Warning: {len(unassigned)} entries outside semester date ranges: {', '.join(dates)}")
    
    return semester_entries


def filter_semesters_with_data(
    semesters: list[SemesterConfig],
    entries: list[TimeEntry]
) -> list[SemesterConfig]:
    """Filter semesters to only those with data.
    
    Args:
        semesters: List of all semesters
        entries: List of all time entries
        
    Returns:
        List of semesters that have at least one entry
    """
    semester_entries = group_entries_by_semester(entries, semesters)
    
    # Return semesters in original order, filtered to those with data
    return [s for s in semesters if s.name in semester_entries]
