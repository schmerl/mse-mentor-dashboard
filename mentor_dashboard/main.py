"""Main entry point for mentor dashboard generation."""

import argparse
import sys
from pathlib import Path

from .data_parser import parse_csv_file
from .name_resolver import NameResolver
from .config_loader import load_config, validate_config, get_semester_by_name
from .semester_filter import (
    filter_semesters_with_data,
    get_latest_semester_with_data,
    group_entries_by_semester,
)


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
        help=(
            "Comma-separated list of semester names to include. "
            "Use 'all' for all semesters with data "
            "(default: latest semester with data)"
        )
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
            print("Error: Configuration validation failed:", file=sys.stderr)
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
            semester_names = [s.strip() for s in args.semesters.split(",") if s.strip()]
            includes_all = any(name.lower() == "all" for name in semester_names)
            if includes_all:
                if len(semester_names) > 1:
                    print(
                        "Warning: '--semesters all' ignores other semester names.",
                        file=sys.stderr,
                    )
                selected_semesters = filter_semesters_with_data(config.semesters, entries)
            else:
                selected_semesters = []
                seen_semester_names: set[str] = set()
                for name in semester_names:
                    semester = get_semester_by_name(config, name)
                    if semester:
                        if semester.name not in seen_semester_names:
                            selected_semesters.append(semester)
                            seen_semester_names.add(semester.name)
                    else:
                        print(f"Warning: Semester '{name}' not found in config", file=sys.stderr)
            if not selected_semesters:
                print("Error: No valid semesters selected", file=sys.stderr)
                sys.exit(1)
        else:
            # Use the latest semester with data by default
            latest_semester = get_latest_semester_with_data(config.semesters, entries)
            if latest_semester is None:
                print("Error: No data found for any semester in the configured date ranges", file=sys.stderr)
                sys.exit(1)
            selected_semesters = [latest_semester]
        
        if args.verbose:
            print(f"Semesters to include: {', '.join(s.name for s in selected_semesters)}")
            print()
        
        # Generate report(s) for each selected semester.
        semester_entries_dict = group_entries_by_semester(entries, selected_semesters)
        semesters_with_entries = [
            semester
            for semester in selected_semesters
            if semester_entries_dict.get(semester.name)
        ]
        if not semesters_with_entries:
            print(
                "Error: No entries found for the selected semester(s)",
                file=sys.stderr,
            )
            sys.exit(1)
        if len(semesters_with_entries) < len(selected_semesters):
            missing = [
                semester.name
                for semester in selected_semesters
                if semester.name not in semester_entries_dict
            ]
            print(
                f"Warning: Skipping semester(s) with no data: {', '.join(missing)}",
                file=sys.stderr,
            )
        if args.verbose:
            mode_text = (
                "separate PDF reports for each team"
                if args.split_by_team
                else "combined PDF report"
            )
            print(f"Generating {mode_text}...")
        if args.split_by_team:
            from .pdf_generator import generate_team_split_reports_with_semester
            all_output_files: dict[str, dict[str, Path]] = {}
            for semester in semesters_with_entries:
                semester_entries = semester_entries_dict[semester.name]
                semester_output = args.output
                if len(semesters_with_entries) > 1:
                    safe_semester_name = "".join(
                        char if char.isalnum() else "_"
                        for char in semester.name
                    ).strip("_").lower()
                    semester_output = args.output.parent / (
                        f"{args.output.stem}_{safe_semester_name}{args.output.suffix}"
                    )
                if args.verbose:
                    print(
                        f"Processing {len(semester_entries)} entries for {semester.name}",
                    )
                output_files = generate_team_split_reports_with_semester(
                    semester_entries,
                    semester_output,
                    semester,
                )
                all_output_files[semester.name] = output_files
            print("✅ Team reports successfully generated:")
            for semester_name, output_files in all_output_files.items():
                if len(all_output_files) > 1:
                    print(f"   📚 {semester_name}")
                for team, file_path in output_files.items():
                    indent = "      " if len(all_output_files) > 1 else "   "
                    print(f"{indent}📊 {team}: {file_path}")
        else:
            from .pdf_generator import generate_pdf_report_with_semester
            generated_files: list[Path] = []
            for semester in semesters_with_entries:
                semester_entries = semester_entries_dict[semester.name]
                semester_output = args.output
                if len(semesters_with_entries) > 1:
                    safe_semester_name = "".join(
                        char if char.isalnum() else "_"
                        for char in semester.name
                    ).strip("_").lower()
                    semester_output = args.output.parent / (
                        f"{args.output.stem}_{safe_semester_name}{args.output.suffix}"
                    )
                if args.verbose:
                    print(
                        f"Processing {len(semester_entries)} entries for {semester.name}",
                    )
                generate_pdf_report_with_semester(
                    semester_entries,
                    semester_output,
                    semester,
                )
                generated_files.append(semester_output)
            if len(generated_files) == 1:
                print(f"✅ Report successfully generated: {generated_files[0]}")
            else:
                print("✅ Reports successfully generated:")
                for file_path in generated_files:
                    print(f"   📄 {file_path}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()