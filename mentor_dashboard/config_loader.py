"""Configuration loader for semester and roster data from config.yml."""

import typing as t
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml


@dataclass
class Holiday:
    """Represents a single holiday date."""
    
    date: datetime

    def __str__(self) -> str:
        """Return string representation of holiday."""
        return self.date.strftime('%m/%d/%Y')


@dataclass
class Break:
    """Represents a semester break period."""
    
    start: datetime
    end: datetime

    def __str__(self) -> str:
        """Return string representation of break period."""
        return f"{self.start.strftime('%m/%d/%Y')} - {self.end.strftime('%m/%d/%Y')}"


@dataclass
class SemesterConfig:
    """Configuration for a single semester."""
    
    name: str
    start_date: datetime
    end_date: datetime
    hours: float  # Expected hours per week
    holidays: list[Holiday]
    break_period: t.Optional[Break] = None

    def __str__(self) -> str:
        """Return string representation of semester."""
        return f"{self.name} ({self.start_date.strftime('%m/%d/%Y')} - {self.end_date.strftime('%m/%d/%Y')})"


@dataclass
class TeamMember:
    """Represents a team member with contact information."""
    
    name: str
    andrewid: str
    email: str

    def __str__(self) -> str:
        """Return string representation of team member."""
        return f"{self.name} ({self.andrewid})"


@dataclass
class Team:
    """Represents a project team."""
    
    name: str
    client: str
    members: list[TeamMember]

    def __str__(self) -> str:
        """Return string representation of team."""
        return f"{self.name} (Client: {self.client}, {len(self.members)} members)"


@dataclass
class Config:
    """Complete configuration including cohort, semesters, and teams."""
    
    cohort_name: str
    semesters: list[SemesterConfig]
    teams: list[Team]

    def __str__(self) -> str:
        """Return string representation of config."""
        return f"Config: {self.cohort_name}, {len(self.semesters)} semesters, {len(self.teams)} teams"


def _parse_date(date_str: str) -> datetime:
    """Parse a date string in M-D-YYYY format.
    
    Args:
        date_str: Date string in format M-D-YYYY (e.g., "1-12-2026" or "12-31-2026")
        
    Returns:
        Parsed datetime object
        
    Raises:
        ValueError: If date format is invalid
    """
    try:
        # Try parsing as M-D-YYYY
        return datetime.strptime(date_str, '%m-%d-%Y')
    except ValueError:
        try:
            # Try single digit month
            return datetime.strptime(date_str, '%-m-%d-%Y')
        except ValueError:
            # Try single digit month and day
            parts = date_str.split('-')
            if len(parts) == 3:
                month, day, year = parts
                return datetime(int(year), int(month), int(day))
            raise ValueError(f"Invalid date format: {date_str}. Expected M-D-YYYY")


def _parse_holidays(holidays_data: t.Optional[list]) -> list[Holiday]:
    """Parse holiday dates from config data.
    
    Args:
        holidays_data: List of holiday date strings or None
        
    Returns:
        List of Holiday objects
    """
    if not holidays_data:
        return []
    
    holidays = []
    for holiday_str in holidays_data:
        try:
            holiday_date = _parse_date(str(holiday_str))
            holidays.append(Holiday(date=holiday_date))
        except ValueError as e:
            print(f"Warning: Skipping invalid holiday date '{holiday_str}': {e}")
    
    return holidays


def _parse_break(break_data: t.Optional[dict]) -> t.Optional[Break]:
    """Parse break period from config data.
    
    Args:
        break_data: Dictionary with 'start' and 'end' keys or None
        
    Returns:
        Break object or None if no break data
    """
    if not break_data:
        return None
    
    try:
        start_date = _parse_date(break_data['start'])
        end_date = _parse_date(break_data['end'])
        return Break(start=start_date, end=end_date)
    except (KeyError, ValueError) as e:
        print(f"Warning: Invalid break data: {e}")
        return None


def _parse_semester(semester_data: dict) -> t.Optional[SemesterConfig]:
    """Parse a single semester configuration.
    
    Args:
        semester_data: Dictionary containing semester configuration
        
    Returns:
        SemesterConfig object or None if parsing fails
    """
    try:
        name = semester_data['semester']
        dates = semester_data['dates']
        
        start_date = _parse_date(dates['start'])
        end_date = _parse_date(dates['end'])
        hours = float(dates.get('hours', 0))
        
        holidays = _parse_holidays(dates.get('holidays'))
        break_period = _parse_break(dates.get('break'))
        
        return SemesterConfig(
            name=name,
            start_date=start_date,
            end_date=end_date,
            hours=hours,
            holidays=holidays,
            break_period=break_period
        )
    except (KeyError, ValueError) as e:
        print(f"Warning: Failed to parse semester: {e}")
        return None


def _parse_team_member(member_data: dict) -> t.Optional[TeamMember]:
    """Parse a single team member.
    
    Args:
        member_data: Dictionary containing member information
        
    Returns:
        TeamMember object or None if parsing fails
    """
    try:
        return TeamMember(
            name=member_data['name'],
            andrewid=member_data['andrewid'],
            email=member_data['email']
        )
    except KeyError as e:
        print(f"Warning: Failed to parse team member: {e}")
        return None


def _parse_team(team_data: dict) -> t.Optional[Team]:
    """Parse a single team configuration.
    
    Args:
        team_data: Dictionary containing team configuration
        
    Returns:
        Team object or None if parsing fails
    """
    try:
        name = team_data['team']
        client = team_data['client']
        members_data = team_data.get('members', [])
        
        members = []
        for member_data in members_data:
            member = _parse_team_member(member_data)
            if member:
                members.append(member)
        
        return Team(name=name, client=client, members=members)
    except KeyError as e:
        print(f"Warning: Failed to parse team: {e}")
        return None


def load_config(path: Path) -> Config:
    """Load and parse configuration from YAML file.
    
    Args:
        path: Path to config.yml file
        
    Returns:
        Config object with parsed configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is invalid
        ValueError: If required fields are missing
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    if not data:
        raise ValueError("Config file is empty")
    
    # Parse cohort info
    cohort_data = data.get('cohort', {})
    cohort_name = cohort_data.get('name', 'Unknown Cohort')
    
    # Parse semesters
    semesters = []
    semesters_data = cohort_data.get('semesters', [])
    for semester_data in semesters_data:
        semester = _parse_semester(semester_data)
        if semester:
            semesters.append(semester)
    
    if not semesters:
        raise ValueError("No valid semesters found in config")
    
    # Parse teams/roster
    teams = []
    teams_data = data.get('roster', [])
    for team_data in teams_data:
        team = _parse_team(team_data)
        if team:
            teams.append(team)
    
    return Config(
        cohort_name=cohort_name,
        semesters=semesters,
        teams=teams
    )


def validate_config(config: Config) -> list[str]:
    """Validate configuration and return list of errors.
    
    Args:
        config: Config object to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Validate semesters
    if not config.semesters:
        errors.append("No semesters defined")
    
    for semester in config.semesters:
        if semester.start_date >= semester.end_date:
            errors.append(f"Semester {semester.name}: start date must be before end date")
        
        if semester.hours <= 0:
            errors.append(f"Semester {semester.name}: expected hours must be positive")
        
        if semester.break_period:
            if semester.break_period.start >= semester.break_period.end:
                errors.append(f"Semester {semester.name}: break start must be before break end")
            
            if (semester.break_period.start < semester.start_date or 
                semester.break_period.end > semester.end_date):
                errors.append(f"Semester {semester.name}: break period outside semester dates")
    
    # Validate teams
    for team in config.teams:
        if not team.members:
            errors.append(f"Team {team.name}: no members defined")
    
    return errors


def get_semester_by_name(config: Config, name: str) -> t.Optional[SemesterConfig]:
    """Get semester configuration by name.
    
    Args:
        config: Config object
        name: Semester name to find
        
    Returns:
        SemesterConfig object or None if not found
    """
    for semester in config.semesters:
        if semester.name == name:
            return semester
    return None


def get_team_by_name(config: Config, name: str) -> t.Optional[Team]:
    """Get team configuration by name.
    
    Args:
        config: Config object
        name: Team name to find
        
    Returns:
        Team object or None if not found
    """
    for team in config.teams:
        if team.name == name:
            return team
    return None
