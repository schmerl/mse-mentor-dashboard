"""Generate pie charts and visualizations for time tracking data."""

import typing as t
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure

from .data_parser import TimeEntry


# Global color mapping for categories to ensure consistency across all pie charts
_CATEGORY_COLOR_MAP: dict[str, str] = {}
_ACTIVITY_COLOR_MAP: dict[str, str] = {}


def get_chart_colors(num_colors: int) -> list[str]:
    """Get a colorblind-friendly color palette.
    
    Args:
        num_colors: Number of colors needed
        
    Returns:
        List of hex color codes
    """
    # Colorblind-friendly palette based on Paul Tol's scheme
    base_colors = [
        '#1f77b4',  # blue
        '#ff7f0e',  # orange  
        '#2ca02c',  # green
        '#d62728',  # red
        '#9467bd',  # purple
        '#8c564b',  # brown
        '#e377c2',  # pink
        '#7f7f7f',  # gray
        '#bcbd22',  # olive
        '#17becf',  # cyan
        '#aec7e8',  # light blue
        '#ffbb78',  # light orange
        '#98df8a',  # light green
        '#ff9896',  # light red
        '#c5b0d5',  # light purple
    ]
    
    # If we need more colors, cycle through with alpha variations
    if num_colors <= len(base_colors):
        return base_colors[:num_colors]
    else:
        # Return base colors and then repeat with variations
        colors = base_colors[:]
        while len(colors) < num_colors:
            colors.extend(base_colors[:min(num_colors - len(colors), len(base_colors))])
        return colors[:num_colors]


def get_consistent_colors_for_labels(labels: list[str], chart_type: str = 'category') -> list[str]:
    """Get consistent colors for labels across all charts.
    
    Args:
        labels: List of category or activity labels
        chart_type: Either 'category' or 'activity' for different color mappings
        
    Returns:
        List of colors corresponding to the labels
    """
    # Choose the appropriate color map
    color_map = _CATEGORY_COLOR_MAP if chart_type == 'category' else _ACTIVITY_COLOR_MAP
    base_colors = get_chart_colors(50)  # Get a large palette to choose from
    
    colors = []
    next_color_index = len(color_map)  # Start assigning new colors from where we left off
    
    for label in labels:
        if label not in color_map:
            # Assign a new color to this label
            color_map[label] = base_colors[next_color_index % len(base_colors)]
            next_color_index += 1
        colors.append(color_map[label])
    
    return colors


def create_pie_chart(data: dict[str, float], title: str, figsize: tuple[float, float] = (8, 6), chart_type: str = 'category') -> Figure:
    """Create a pie chart from data dictionary.
    
    Args:
        data: Dictionary mapping labels to values
        title: Chart title
        figsize: Figure size as (width, height)
        chart_type: Either 'category' or 'activity' for consistent color mapping
        
    Returns:
        matplotlib Figure object
    """
    if not data:
        # Create empty chart
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', 
                transform=ax.transAxes, fontsize=14)
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.axis('off')
        return fig
    
    # Sort data by value (descending)
    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    labels = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]
    
    # Get consistent colors for labels
    colors = get_consistent_colors_for_labels(labels, chart_type)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)
    
    # Create pie chart
    wedges, texts, autotexts = ax.pie(
        values, 
        labels=None,  # We'll add custom legend
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        textprops={'fontsize': 10}
    )
    
    # Customize percentage text
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    # Add title
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # Create legend with hours and larger font size
    legend_labels = [f'{label}: {value:.1f}h' for label, value in sorted_items]
    ax.legend(wedges, legend_labels, loc='center left', bbox_to_anchor=(1, 0.5), fontsize=12)
    
    # Equal aspect ratio ensures pie is circular
    ax.axis('equal')
    
    plt.tight_layout()
    return fig


def create_individual_charts(entries: list[TimeEntry], user: str) -> tuple[Figure, Figure]:
    """Create category and activity pie charts for an individual user.
    
    Args:
        entries: List of time entries for the user
        user: User name
        
    Returns:
        Tuple of (category_chart, activity_chart) figures
    """
    # Aggregate data by category and activity
    categories: dict[str, float] = {}
    activities: dict[str, float] = {}
    
    for entry in entries:
        categories[entry.category] = categories.get(entry.category, 0) + entry.duration_hours
        activities[entry.activity] = activities.get(entry.activity, 0) + entry.duration_hours
    
    # Create charts with consistent colors
    category_chart = create_pie_chart(
        categories, 
        f'{user} - Time by Category',
        figsize=(10, 8),
        chart_type='category'
    )
    
    activity_chart = create_pie_chart(
        activities, 
        f'{user} - Time by Activity',
        figsize=(10, 8),
        chart_type='activity'
    )
    
    return category_chart, activity_chart


def create_team_charts(entries: list[TimeEntry], team: str) -> tuple[Figure, Figure]:
    """Create category and activity pie charts for a team.
    
    Args:
        entries: List of time entries for the team
        team: Team name
        
    Returns:
        Tuple of (category_chart, activity_chart) figures
    """
    # Aggregate data by category and activity
    categories: dict[str, float] = {}
    activities: dict[str, float] = {}
    
    for entry in entries:
        categories[entry.category] = categories.get(entry.category, 0) + entry.duration_hours
        activities[entry.activity] = activities.get(entry.activity, 0) + entry.duration_hours
    
    # Create charts with consistent colors
    category_chart = create_pie_chart(
        categories, 
        f'Team {team} - Total Time by Category',
        figsize=(10, 8),
        chart_type='category'
    )
    
    activity_chart = create_pie_chart(
        activities, 
        f'Team {team} - Total Time by Activity',
        figsize=(10, 8),
        chart_type='activity'
    )
    
    return category_chart, activity_chart


def create_trend_indicator(current_value: float, previous_value: float, is_new: bool = False) -> str:
    """Create trend indicator based on current vs previous values.
    
    Args:
        current_value: Current week's value
        previous_value: Previous week's value  
        is_new: True if this is a new activity/category
        
    Returns:
        String with trend indicator (↑, ↓, →, ★)
    """
    if is_new:
        return '★'
    
    if previous_value == 0:
        return '★' if current_value > 0 else '→'
    
    # Calculate percentage change
    change_percent = (current_value - previous_value) / previous_value * 100
    
    if change_percent > 5:  # More than 5% increase
        return '↑'
    elif change_percent < -5:  # More than 5% decrease
        return '↓'
    else:
        return '→'


def figure_to_bytes(figure: Figure) -> BytesIO:
    """Convert matplotlib figure to BytesIO for embedding in PDF.
    
    Args:
        figure: matplotlib Figure object
        
    Returns:
        BytesIO buffer containing PNG image data
    """
    buffer = BytesIO()
    figure.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    plt.close(figure)  # Free memory
    return buffer


def create_individual_trend_chart(user_name: str, user_weekly_data: dict, team_avg_data: dict, 
                                  all_teams_avg_data: dict, figsize: tuple[float, float] = (10, 6)) -> Figure:
    """Create line chart showing individual user's weekly hours with team and global averages.
    
    Args:
        user_name: Name of the user
        user_weekly_data: Dict mapping week_start -> hours for the user
        team_avg_data: Dict mapping week_start -> average hours for user's team
        all_teams_avg_data: Dict mapping week_start -> average hours across all teams
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    if not user_weekly_data:
        # Create empty chart
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', 
                transform=ax.transAxes, fontsize=14)
        ax.set_title(f'{user_name} - Weekly Hours Trend', fontsize=16, fontweight='bold')
        ax.axis('off')
        return fig
    
    # Sort weeks chronologically
    weeks = sorted(user_weekly_data.keys())
    user_hours = [user_weekly_data[week] for week in weeks]
    team_avg_hours = [team_avg_data.get(week, 0) for week in weeks]
    all_teams_avg_hours = [all_teams_avg_data.get(week, 0) for week in weeks]
    
    # Create week labels (just show dates)
    week_labels = [week.strftime('%m/%d') for week in weeks]
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot lines
    ax.plot(week_labels, user_hours, 'o-', linewidth=3, markersize=8, 
            color='#1f77b4', label=f'{user_name}', zorder=3)
    ax.plot(week_labels, team_avg_hours, '--', linewidth=2, 
            color='#ff7f0e', label='Team Average', alpha=0.8, zorder=2)
    ax.plot(week_labels, all_teams_avg_hours, ':', linewidth=2, 
            color='#2ca02c', label='All Teams Average', alpha=0.8, zorder=1)
    
    # Customize chart
    ax.set_title(f'{user_name} - Weekly Hours Trend', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Week Starting', fontsize=12, fontweight='bold')
    ax.set_ylabel('Hours', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', framealpha=0.9)
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Set y-axis to start at 0
    ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    return fig


def create_team_comparison_chart(team_name: str, all_teams_weekly_data: dict, 
                                figsize: tuple[float, float] = (12, 7)) -> Figure:
    """Create line chart comparing all teams' weekly hours.
    
    Args:
        team_name: Name of the current team (for highlighting)
        all_teams_weekly_data: Dict mapping team_name -> {week_start -> total_hours}
        figsize: Figure size
        
    Returns:
        matplotlib Figure object
    """
    if not all_teams_weekly_data:
        # Create empty chart
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', 
                transform=ax.transAxes, fontsize=14)
        ax.set_title('Team Comparison - Weekly Hours', fontsize=16, fontweight='bold')
        ax.axis('off')
        return fig
    
    # Get all unique weeks across all teams
    all_weeks = set()
    for team_data in all_teams_weekly_data.values():
        all_weeks.update(team_data.keys())
    weeks = sorted(all_weeks)
    
    if not weeks:
        # Create empty chart
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No weeks data available', ha='center', va='center', 
                transform=ax.transAxes, fontsize=14)
        ax.set_title('Team Comparison - Weekly Hours', fontsize=16, fontweight='bold')
        ax.axis('off')
        return fig
    
    # Create week labels
    week_labels = [week.strftime('%m/%d') for week in weeks]
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)
    
    # Color palette for teams
    colors = get_chart_colors(len(all_teams_weekly_data))
    
    # Plot each team
    for i, (t_name, team_weekly_data) in enumerate(sorted(all_teams_weekly_data.items())):
        team_hours = [team_weekly_data.get(week, 0) for week in weeks]
        
        # Highlight current team with thicker line and different style
        if t_name == team_name:
            ax.plot(week_labels, team_hours, 'o-', linewidth=4, markersize=10, 
                   color=colors[i], label=f'{t_name} (Current)', zorder=3)
        else:
            ax.plot(week_labels, team_hours, 's-', linewidth=2, markersize=6, 
                   color=colors[i], label=t_name, alpha=0.8, zorder=2)
    
    # Customize chart
    ax.set_title('Team Comparison - Weekly Total Hours', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Week Starting', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Team Hours', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', framealpha=0.9)
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Set y-axis to start at 0
    ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    return fig


def save_chart_as_png(figure: Figure, output_path: Path) -> None:
    """Save matplotlib figure as PNG file.
    
    Args:
        figure: matplotlib Figure object
        output_path: Path to save PNG file
    """
    figure.savefig(output_path, format='png', dpi=150, bbox_inches='tight')
    plt.close(figure)  # Free memory
