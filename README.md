# Mentor Dashboard

Generate weekly time tracking reports and visualizations for project teams based on CSV time tracking data (e.g., from Clockify).

## Features

✅ **Core Functionality:**
- Parse CSV time tracking data with automatic date format detection
- Group data by teams and weeks (Monday-Sunday)
- Generate individual student pie charts (time by category and activity)
- Create team-level aggregate pie charts
- Weekly trend analysis with arrow indicators (↑↓→★)
- Professional PDF output with proper pagination
- Split reports by team (separate PDF for each team)
- Hours tracking with color-coded performance indicators
- **NEW**: Name resolution for proper "First Last" formatting
- **NEW**: Historical trend line charts (individual & team comparisons)

✅ **Data Handling:**
- Handles missing data gracefully (shows as "Uncategorized" or "Unknown")
- Extracts activities and categories from Tags field
- Supports multiple date formats (DD/MM/YYYY, etc.)
- Colorblind-friendly chart colors
- **NEW**: Weeks ordered with most recent first for easy review

## Installation

```bash
# Clone or navigate to the project directory
cd mentor-dashboard

# Install dependencies with uv
uv sync
```

## Usage

### Basic Usage
```bash
# Generate report with expected 20 hours per student per week
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --expected-hours 20
```

### Custom Output Location
```bash
# Specify custom output path (directories created automatically)
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --expected-hours 20 -o "reports/weekly_report.pdf"
```

### Verbose Output
```bash
# Show detailed processing information
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --expected-hours 20 --verbose
```

### Split by Team
```bash
# Generate separate PDF files for each team
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --expected-hours 20 --split-by-team

# Combine with custom output directory
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --expected-hours 15 --split-by-team -o "team_reports/weekly.pdf"
```

### Name Resolution
```bash
# Use roster.csv to display "First Last" names instead of Andrew IDs
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --expected-hours 15 --roster "roster.csv"

# Combine with other options
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --expected-hours 15 --roster "roster.csv" --split-by-team --verbose
```

### Help
```bash
uv run mentor-dashboard --help
```

## CSV Format Requirements

### Time Tracking CSV
Your time tracking CSV file should contain these columns:
- **Project**: Project name
- **User**: Student/user name (can be Andrew ID or full name)
- **Group**: Team identifier
- **Start Date**: Entry start date (supports multiple formats)
- **End Date**: Entry end date
- **Duration (decimal)**: Hours worked (decimal format)
- **Tags**: Contains activity and category info (format: "ACTIVITY: X, CATEGORY: Y")
- **Description**: Task description (optional)
- **Email**: Student email address (optional, used for name resolution)

### Roster CSV (Optional)
For name resolution, provide a roster.csv file with these columns:
- **Last Name**: Student's last name
- **Preferred/First Name**: Student's first/preferred name
- **Andrew ID**: Student's Andrew ID (matches User field or email prefix)
- **Email**: Student's email address (andrew_id@andrew.cmu.edu)

**Name Resolution**: When a roster file is provided, the system automatically converts Andrew IDs to proper "First Last" format. Names already in proper format are preserved unchanged.

## Generated Report Contents

📊 **Title Page:**
- Report date range
- Team overview
- Summary statistics

📈 **Weekly Reports (per team):**
- **Most recent week first** for immediate visibility of current status
- Team summary (total hours, participants, averages)
- Trend analysis tables with arrow indicators:
  - ↑ Increased from previous week
  - ↓ Decreased from previous week  
  - → No significant change
  - ★ New activity/category
  - Includes trend key below each table for easy reference
- **🆕 Student Hours Status** (color-coded performance tracking):
  - 🟢 **Green**: Meeting expectations (85-115% of target)
  - 🟠 **Orange**: Off target by 15-30%
  - 🔴 **Red**: Significantly off target (>30%)
  - Time trend indicators for each student
  - Status key with expected hours reference
- Individual student charts (for most recent week):
  - Time by Category (pie chart)
  - Time by Activity (pie chart)
  - **🆕 Weekly Hours Trend** (line chart with team & global averages)
- **🆕 Team Time Distribution** (performance summary):
  - Total team hours vs. expected (team size × individual target)
  - Average hours per team member
  - Team performance percentage and trend indicator
  - Color-coded status matching individual indicators
- Team aggregate charts (for most recent week):
  - Combined time by Category
  - Combined time by Activity
  - **🆕 Team Performance Comparison** (line chart vs. all other teams)

## Example Output

Running on the provided sample data generates reports for:
- **Teams**: IRAlogix, Troutwood, eParts
- **Time Period**: January 12 - February 2, 2026
- **Total Hours**: 333.2 hours across 15 participants
- **Weeks Covered**: 3+ weeks with trend analysis

## Development

```bash
# Run with development dependencies
uv sync --dev

# Format code
uv run black mentor_dashboard/

# Lint code
uv run ruff mentor_dashboard/
```
