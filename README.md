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

## Configuration

### config.yml

The dashboard now requires a `config.yml` file that defines:
- **Cohort Information**: Name and semester details
- **Semesters**: Start/end dates, expected hours per week, breaks, and holidays
- **Roster**: Team names, client names, and member details (name, Andrew ID, email)

**Example config.yml:**
```yaml
cohort:
  name: MSE Studio
  semesters:
  - semester: Spring 2026
    dates:
      start: 1-12-2026
      end: 4-24-2026
      hours: 12  # Expected hours per week
      break:
        start: 2-28-2026
        end: 3-8-2026
      holidays:
      - 1-19-2026  # MLK Day
      - 4-10-2026  # Good Friday
roster:
  - team: Troutans
    client: Troutwood
    members:
      - name: Noor Buchi
        andrewid: nbuchi
        email: nbuchi@andrew.cmu.edu
```

### Calendar-Aware Expected Hours

The system automatically adjusts expected hours based on the semester calendar:
- **Breaks**: No work expected during break weeks (students may work to make up time)
- **Holidays**: Each weekday holiday reduces expected hours by 1/5 of weekly total
- **Example**: 12 hours/week with Monday holiday = 9.6 hours expected that week

## Usage

### Basic Usage
```bash
# Generate report using config.yml (defaults to latest semester with data)
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --config config.yml
```

### Custom Output Location
```bash
# Specify custom output path
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --config config.yml -o "reports/weekly_report.pdf"
```

### Semester Selection
```bash
# Generate report for specific semester(s)
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --config config.yml --semesters "Spring 2026"

# Multiple semesters (comma-separated)
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --config config.yml --semesters "Spring 2026,Fall 2026"

# All semesters with data
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --config config.yml --semesters all
```

### Verbose Output
```bash
# Show detailed processing information
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --config config.yml --verbose
```

### Split by Team
```bash
# Generate separate PDF files for each team
uv run mentor-dashboard "data/Raw CSV_Detailed.csv" --config config.yml --split-by-team
```

### Help
```bash
uv run mentor-dashboard --help
```

## Student Summary Reports

Generate individual student summaries showing week-by-week participation, hours trends, and activity breakdowns.

### Basic Student Summary
```bash
# Generate summaries for all students (defaults to latest semester with data)
uv run student-summary "data/Raw CSV_Detailed.csv" --config config.yml
```

### Filter by Team
```bash
# Generate summaries for students in a specific team
uv run student-summary "data/Raw CSV_Detailed.csv" --config config.yml --team Troutwood
```

### Filter by Student
```bash
# Generate summary for a specific student
uv run student-summary "data/Raw CSV_Detailed.csv" --config config.yml --student "Luke Kiebert"
```

### Semester Selection
```bash
# Generate summary for specific semester
uv run student-summary "data/Raw CSV_Detailed.csv" --config config.yml --semesters "Spring 2026"

# Generate summaries for all semesters with data
uv run student-summary "data/Raw CSV_Detailed.csv" --config config.yml --semesters all
```

### Combined Filters
```bash
# Team + student filter with custom output
uv run student-summary "data/Raw CSV_Detailed.csv" --config config.yml --team Troutwood --student "Luke Kiebert" -o student_luke.pdf
```

### Student Summary Report Contents

📋 **Title Page:**
- Total number of students
- Total hours logged across all students
- Average hours per student
- Expected hours per week

👤 **Per-Student Pages:**
- Student name and team
- Summary statistics (total hours, weeks active, average per week)
- **Weekly Hours Table:**
  - Week-by-week breakdown (most recent first)
  - Hours logged each week
  - Color-coded status (meeting/above/below expectations)
- **Hours Trend Chart:**
  - Line chart showing weekly hours
  - Expected hours reference line
- **Time Distribution Charts:**
  - Time by Category (pie chart)
  - Time by Activity (pie chart)
  - Aggregated across all weeks

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

### Config.yml
Provides semester configuration and roster information:
- **Cohort Information**: Program name and semester details
- **Semesters**: Each semester includes:
  - **start/end dates**: Semester boundary dates (M-D-YYYY format)
  - **hours**: Expected hours per student per week
  - **break**: Optional mid-semester break period (start/end dates)
  - **holidays**: List of holiday dates (weekdays only affect expected hours)
- **Roster**: Team and member information:
  - **team**: Team name
  - **client**: Client/project name
  - **members**: List with name, andrewid, email for each student

**Name Resolution**: The roster in config.yml automatically converts Andrew IDs to proper "First Last" format. Names already in proper format are preserved unchanged.

### Migration from Old CLI
The old `--expected-hours` and `--roster` arguments have been replaced with `--config`:
- **Before**: `--expected-hours 12 --roster roster.csv`
- **After**: `--config config.yml` (hours and roster now in config file)

See `config.yml` in the repository for a complete example.

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
