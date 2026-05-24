"""Main entry point for mentor dashboard generation."""

import argparse
import sys
import typing as t
from pathlib import Path

from .data_parser import parse_csv_file
from .name_resolver import NameResolver
from .config_loader import load_config, validate_config, get_semester_by_name
from .semester_filter import group_entries_by_semester, filter_semesters_with_data
from .pdf_generator import generate_pdf_report


def main() -> None:
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(
        description="Generate weekly time tracking reports and visualizations for project teams"
    )
    
    parser.add_argument(
        "csv_file",
        type=Path,
        help="Path to the CSV file containing time tracking data"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to config.yml file with semester and roster configuration"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output PDF file path (default: mentor_dashboard_report.pdf)"
    )
    
    parser.add_argument(
        "--semesters",
        type=str,
        help="Comma-separated list of semester names to include (default: all semesters with data)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--split-by-team",
        action="store_true",
        help="Create separate PDF files for each team"
    )
    
    args = parser.parse_args()
    
    # Set default output path if not provided
    if args.output is None:
        args.output = Path("mentor_dashboard_report.pdf")
    
    # Create output directory if it doesn't exist
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # Validate input files exist
    if not args.csv_file.exists():
        print(f"Error: CSV file '{args.csv_file}' not found.", file=sys.stderr)
        sys.exit(1)
    
    if not args.config.exists():
        print(f"Error: Config file '{args.config}' not found.", file=sys.stderr)
        sys.exit(1)
    
    if args.verbose:
        print(f"Processing CSV file: {args.csv_file}")
        print(f"Loading config: {args.config}")
        print(f"Output will be saved to: {args.output}")
    
    try:
        # Load configuration
        if args.verbose:
            print("Loading configuration...")
        
        config = load_config(args.config)
        
        # Validate configuration
        errors = validate_config(config)
        if errors:
            print(f"Error: Configuration validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)
        
        if args.verbose:
            print(f"✓ Loaded config: {config}")
        
        # Initialize name resolver from config
        name_resolver = NameResolver.from_config(config.teams)
        if args.verbose:
            stats = name_resolver.get_stats()
            print(f"✓ Name resolver loaded: {stats['total_names_in_roster']} names")
        
        # Parse CSV data
        if args.verbose:
            print("Parsing CSV data...")
        
        entries = parse_csv_file(args.csv_file, name_resolver)
        
        if args.verbose:
            print(f"Successfully parsed {len(entries)} time entries")
            
            # Show summary statistics
            teams = set(entry.group for entry in entries)
            users = set(entry.user for entry in entries)
            total_hours = sum(entry.duration_hours for entry in entries)
            
            print(f"Teams found: {', '.join(sorted(teams))}")
            print(f"Users: {len(users)}")
            print(f"Total hours logged: {total_hours:.1f}")
            print()
        
        # Determine which semesters to include
        if args.semesters:
            # Parse comma-separated list
            semester_names = [s.strip() for s in args.semesters.split(',')]
            selected_semesters = []
            for name in semester_names:
                semester = get_semester_by_name(config, name)
                if semester:
                    selected_semesters.append(semester)
                else:
                    print(f"Warning: Semester '{name}' not found in config", file=sys.stderr)
            
            if not selected_semesters:
                print(f"Error: No valid semesters selected", file=sys.stderr)
                sys.exit(1)
        else:
            # Use all semesters with data
            selected_semesters = filter_semesters_with_data(config.semesters, entries)
            
            if not selected_semesters:
                print(f"Error: No data found for any semester in the configured date ranges", file=sys.stderr)
                sys.exit(1)
        
        if args.verbose:
            print(f"Semesters to include: {', '.join(s.name for s in selected_semesters)}")
            print()
        
        # Generate PDF report(s)
        # For now, we'll generate a single-semester report for the first semester
        # Multi-semester support will be added in the next step
        if len(selected_semesters) > 1:
            print(f"Warning: Multi-semester reporting not yet fully implemented. Using first semester: {selected_semesters[0].name}", file=sys.stderr)
        
        semester = selected_semesters[0]
        semester_entries_dict = group_entries_by_semester(entries, [semester])
        semester_entries = semester_entries_dict.get(semester.name, [])
        
        if not semester_entries:
            print(f"Error: No entries found for semester {semester.name}", file=sys.stderr)
            sys.exit(1)
        
        if args.verbose:
            print(f"Processing {len(semester_entries)} entries for {semester.name}")
            if args.split_by_team:
                print("Generating separate PDF reports for each team...")
            else:
                print("Generating combined PDF report...")
        
        # Pass semester config for calendar-aware expected hours
        if args.split_by_team:
            from .pdf_generator import generate_team_split_reports_with_semester
            output_files = generate_team_split_reports_with_semester(semester_entries, args.output, semester)
            
            print(f"✅ Team reports successfully generated:")
            for team, file_path in output_files.items():
                print(f"   📊 {team}: {file_path}")
        else:
            from .pdf_generator import generate_pdf_report_with_semester
            generate_pdf_report_with_semester(semester_entries, args.output, semester)
            print(f"✅ Report successfully generated: {args.output}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()