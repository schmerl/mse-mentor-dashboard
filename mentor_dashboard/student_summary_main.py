"""Main entry point for student summary generation."""

import argparse
import sys
import typing as t
from pathlib import Path

from .data_parser import parse_csv_file
from .name_resolver import NameResolver
from .config_loader import load_config, validate_config, get_semester_by_name
from .semester_filter import group_entries_by_semester, filter_semesters_with_data
from .report_generator import generate_student_summary_data
from .pdf_generator import generate_student_summary_pdf


def main() -> None:
    """Main function for student summary command-line interface."""
    parser = argparse.ArgumentParser(
        description="Generate individual student summary reports with week-by-week participation"
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
        "--semesters",
        type=str,
        help="Comma-separated list of semester names to include (default: all semesters with data)"
    )
    
    parser.add_argument(
        "--team",
        type=str,
        help="Filter by team name"
    )
    
    parser.add_argument(
        "--student",
        type=str,
        help="Filter by student name"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output PDF file path (default: student_summary_report.pdf)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Set default output path if not provided
    if args.output is None:
        args.output = Path("student_summary_report.pdf")
    
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
        if args.team:
            print(f"Filtering by team: {args.team}")
        if args.student:
            print(f"Filtering by student: {args.student}")
    
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
        
        # Determine which semesters to include
        if args.semesters:
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
            selected_semesters = filter_semesters_with_data(config.semesters, entries)
            
            if not selected_semesters:
                print(f"Error: No data found for any semester", file=sys.stderr)
                sys.exit(1)
        
        if args.verbose:
            print(f"Semesters to include: {', '.join(s.name for s in selected_semesters)}")
        
        # For now, use first semester (multi-semester support to be added)
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
        
        # Generate student summaries
        if args.verbose:
            print("Generating student summaries...")
        
        summaries = generate_student_summary_data(
            semester_entries,
            team_filter=args.team,
            student_filter=args.student
        )
        
        if not summaries:
            print("No student data found matching the specified filters.", file=sys.stderr)
            sys.exit(1)
        
        if args.verbose:
            print(f"Generated summaries for {len(summaries)} student(s)")
            for summary in summaries:
                print(f"  - {summary.name} ({summary.team}): {summary.total_hours:.1f}h total")
        
        # Generate PDF report
        if args.verbose:
            print("Generating PDF report...")
        
        # Pass semester config for calendar-aware expected hours
        from .pdf_generator import generate_student_summary_pdf_with_semester
        generate_student_summary_pdf_with_semester(summaries, args.output, semester, semester_entries)
        
        print(f"✅ Student summary report successfully generated: {args.output}")
        
    except Exception as e:
        print(f"❌ Error generating student summary: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
