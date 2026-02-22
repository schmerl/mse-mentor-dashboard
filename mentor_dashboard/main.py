"""Main entry point for mentor dashboard generation."""

import argparse
import sys
import typing as t
from pathlib import Path

from .data_parser import parse_csv_file
from .name_resolver import NameResolver
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
        "-o", "--output",
        type=Path,
        help="Output PDF file path (default: mentor_dashboard_report.pdf)"
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
    
    args = parser.parse_args()
    
    # Set default output path if not provided
    if args.output is None:
        args.output = Path("mentor_dashboard_report.pdf")
    
    # Create output directory if it doesn't exist
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # Validate input file exists
    if not args.csv_file.exists():
        print(f"Error: CSV file '{args.csv_file}' not found.", file=sys.stderr)
        sys.exit(1)
    
    if args.verbose:
        print(f"Processing CSV file: {args.csv_file}")
        print(f"Output will be saved to: {args.output}")
    
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
            
            # Show summary statistics
            teams = set(entry.group for entry in entries)
            users = set(entry.user for entry in entries)
            total_hours = sum(entry.duration_hours for entry in entries)
            
            print(f"Teams found: {', '.join(sorted(teams))}")
            print(f"Users: {len(users)}")
            print(f"Total hours logged: {total_hours:.1f}")
            print()
        
        # Generate PDF report(s)
        if args.verbose:
            if args.split_by_team:
                print("Generating separate PDF reports for each team...")
            else:
                print("Generating combined PDF report...")
        
        if args.split_by_team:
            from .pdf_generator import generate_team_split_reports
            output_files = generate_team_split_reports(entries, args.output, args.expected_hours)
            
            print(f"✅ Team reports successfully generated:")
            for team, file_path in output_files.items():
                print(f"   📊 {team}: {file_path}")
        else:
            from .pdf_generator import generate_pdf_report
            generate_pdf_report(entries, args.output, args.expected_hours)
            print(f"✅ Report successfully generated: {args.output}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()