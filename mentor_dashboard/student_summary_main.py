"""Main entry point for student summary generation."""

import argparse
import sys
import typing as t
from pathlib import Path

from .data_parser import parse_csv_file
from .name_resolver import NameResolver
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
        "--expected-hours",
        type=float,
        required=True,
        help="Expected number of hours per student per week"
    )
    
    parser.add_argument(
        "--roster",
        type=Path,
        help="Path to roster.csv file for name resolution (displays 'First Last' names)"
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
    
    # Validate input file exists
    if not args.csv_file.exists():
        print(f"Error: CSV file '{args.csv_file}' not found.", file=sys.stderr)
        sys.exit(1)
    
    if args.verbose:
        print(f"Processing CSV file: {args.csv_file}")
        print(f"Output will be saved to: {args.output}")
        if args.team:
            print(f"Filtering by team: {args.team}")
        if args.student:
            print(f"Filtering by student: {args.student}")
    
    try:
        # Initialize name resolver if roster file provided
        name_resolver = None
        if args.roster:
            if not args.roster.exists():
                print(f"Warning: Roster file '{args.roster}' not found. Names will not be resolved.", file=sys.stderr)
            else:
                if args.verbose:
                    print(f"Loading roster file: {args.roster}")
                try:
                    name_resolver = NameResolver(str(args.roster))
                    stats = name_resolver.get_stats()
                    if args.verbose:
                        print(f"Name resolver loaded: {stats['total_names_in_roster']} names from {stats['roster_entries']} roster entries")
                except Exception as e:
                    print(f"Warning: Could not load roster file: {e}. Names will not be resolved.", file=sys.stderr)
        
        # Parse CSV data
        if args.verbose:
            print("Parsing CSV data...")
        
        entries = parse_csv_file(args.csv_file, name_resolver)
        
        if args.verbose:
            print(f"Successfully parsed {len(entries)} time entries")
        
        # Generate student summaries
        if args.verbose:
            print("Generating student summaries...")
        
        summaries = generate_student_summary_data(
            entries,
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
        
        generate_student_summary_pdf(summaries, args.output, args.expected_hours, entries)
        
        print(f"✅ Student summary report successfully generated: {args.output}")
        
    except Exception as e:
        print(f"❌ Error generating student summary: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
