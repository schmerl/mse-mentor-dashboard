"""Generate PDF reports from weekly data and charts."""

import typing as t
from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
)
from reportlab.platypus.flowables import KeepTogether

from .data_parser import TimeEntry, group_entries_by_team_and_week
from .report_generator import (
    WeeklyReport, generate_weekly_reports, generate_user_charts_for_week,
    generate_team_charts_for_week, format_week_range, get_hours_status_color,
    calculate_user_time_trends, get_user_historical_data, get_all_teams_historical_data
)
from .charts import create_individual_trend_chart, create_team_comparison_chart, figure_to_bytes


class MentorDashboardPDF:
    """PDF generator for mentor dashboard reports."""
    
    def __init__(self, output_path: Path, page_size: tuple = A4):
        """Initialize PDF generator.
        
        Args:
            output_path: Path where PDF should be saved
            page_size: Page size tuple (default A4)
        """
        self.output_path = output_path
        self.page_size = page_size
        self.doc = SimpleDocTemplate(
            str(output_path),
            pagesize=page_size,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.story: list = []
    
    def _setup_custom_styles(self) -> None:
        """Set up custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1f77b4'),
            alignment=1  # Center alignment
        ))
        
        # Team title style
        self.styles.add(ParagraphStyle(
            name='TeamTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.HexColor('#d62728'),
            keepWithNext=1
        ))
        
        # Week title style
        self.styles.add(ParagraphStyle(
            name='WeekTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#2ca02c'),
            keepWithNext=1
        ))
        
        # Summary style
        self.styles.add(ParagraphStyle(
            name='Summary',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            leftIndent=20
        ))
        
        # Trend key style
        self.styles.add(ParagraphStyle(
            name='TrendKey',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            leftIndent=20,
            spaceAfter=8
        ))
    
    def add_title_page(self, entries: list[TimeEntry]) -> None:
        """Add title page with report overview.
        
        Args:
            entries: All time entries for date range calculation
        """
        # Calculate date range
        dates = [entry.start_date for entry in entries]
        start_date = min(dates)
        end_date = max(dates)
        
        # Get team names
        teams = sorted(set(entry.group for entry in entries))
        
        # Title
        title = Paragraph("Mentor Dashboard Report", self.styles['CustomTitle'])
        self.story.append(title)
        self.story.append(Spacer(1, 20))
        
        # Date range
        date_range = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
        date_para = Paragraph(f"<b>Report Period:</b> {date_range}", self.styles['Heading2'])
        self.story.append(date_para)
        self.story.append(Spacer(1, 20))
        
        # Teams overview
        teams_text = ", ".join(teams)
        teams_para = Paragraph(f"<b>Teams:</b> {teams_text}", self.styles['Heading2'])
        self.story.append(teams_para)
        self.story.append(Spacer(1, 20))
        
        # Summary stats
        total_hours = sum(entry.duration_hours for entry in entries)
        unique_users = len(set(entry.user for entry in entries))
        
        summary_data = [
            ["Total Hours Logged", f"{total_hours:.1f} hours"],
            ["Number of Participants", str(unique_users)],
            ["Number of Teams", str(len(teams))],
            ["Generated", datetime.now().strftime('%B %d, %Y at %I:%M %p')]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        self.story.append(summary_table)
        self.story.append(PageBreak())
    
    def _add_team_title_page(self, entries: list[TimeEntry], team_name: str) -> None:
        """Add team-specific title page.
        
        Args:
            entries: Time entries for this team only
            team_name: Name of the team
        """
        # Calculate date range for this team
        dates = [entry.start_date for entry in entries]
        start_date = min(dates)
        end_date = max(dates)
        
        # Title
        title = Paragraph(f"Team {team_name} - Weekly Report", self.styles['CustomTitle'])
        self.story.append(title)
        self.story.append(Spacer(1, 20))
        
        # Date range
        date_range = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
        date_para = Paragraph(f"<b>Report Period:</b> {date_range}", self.styles['Heading2'])
        self.story.append(date_para)
        self.story.append(Spacer(1, 20))
        
        # Team members
        team_members = sorted(set(entry.user for entry in entries))
        members_text = ", ".join(team_members)
        members_para = Paragraph(f"<b>Team Members:</b> {members_text}", self.styles['Heading2'])
        self.story.append(members_para)
        self.story.append(Spacer(1, 20))
        
        # Summary stats for this team
        total_hours = sum(entry.duration_hours for entry in entries)
        unique_users = len(team_members)
        
        # Calculate number of weeks
        weeks = set(entry.week_start for entry in entries)
        num_weeks = len(weeks)
        
        summary_data = [
            ["Total Hours Logged", f"{total_hours:.1f} hours"],
            ["Team Members", str(unique_users)],
            ["Weeks Covered", str(num_weeks)],
            ["Average Hours per Week", f"{total_hours / num_weeks:.1f} hours" if num_weeks > 0 else "N/A"],
            ["Generated", datetime.now().strftime('%B %d, %Y at %I:%M %p')]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        self.story.append(summary_table)
        self.story.append(PageBreak())
    
    def _add_student_hours_status(self, report: WeeklyReport, expected_hours: float) -> None:
        """Add student hours status section with color-coded warnings.
        
        Args:
            report: Weekly report with individual summaries
            expected_hours: Expected hours per student per week
        """
        status_title = Paragraph("Student Hours Status", self.styles['Heading4'])
        self.story.append(status_title)
        self.story.append(Spacer(1, 6))
        
        # Add simple legend
        legend_text = (
            "<font color='#006600'>🟢 Meeting Expectations</font> | "
            "<font color='#FF8800'>🟠 Off Target</font> | "
            "<font color='#CC0000'>🔴 Significantly Off Target</font>"
        )
        legend_para = Paragraph(legend_text, ParagraphStyle(
            'Legend', parent=self.styles['Normal'], fontSize=8,
            leftIndent=20, spaceAfter=6
        ))
        self.story.append(legend_para)
        self.story.append(Spacer(1, 6))
        
        # Create status table
        table_data = [["Student", "Hours This Week", "Status", "Time Trend"]]
        
        # Sort students by hours (descending)
        sorted_users = sorted(report.individual_summaries.items(), 
                            key=lambda x: x[1]['total_hours'], reverse=True)
        
        for user, user_summary in sorted_users:
            actual_hours = user_summary['total_hours']
            color_hex, status_text = get_hours_status_color(actual_hours, expected_hours)
            
            # Calculate time trend (placeholder for now - would need historical data)
            # For now, just show current week vs target
            time_trend = self._get_simple_trend(actual_hours, expected_hours)
            
            # Create formatted paragraphs for colored text
            hours_para = Paragraph(f'<b>{actual_hours:.1f}h</b>', ParagraphStyle(
                'HoursStyle', parent=self.styles['Normal'], fontSize=9,
                textColor=colors.HexColor(color_hex), alignment=1
            ))
            
            status_para = Paragraph(status_text, ParagraphStyle(
                'StatusStyle', parent=self.styles['Normal'], fontSize=9,
                textColor=colors.HexColor(color_hex), alignment=0
            ))
            
            table_data.append([user, hours_para, status_para, time_trend])
        
        # Create table
        status_table = Table(table_data, colWidths=[2*inch, 1.2*inch, 2.2*inch, 0.8*inch])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6f3ff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),     # Names left-aligned
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),   # Hours centered
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),     # Status left-aligned
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),   # Trend centered
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        
        self.story.append(status_table)
        self.story.append(Spacer(1, 6))
        
        # Add status key with proper color formatting
        status_key_text = (
            f"<b>Expected Hours:</b> {expected_hours:.1f}h/week | "
            "<font color='#006600'><b>Green:</b> Meeting expectations</font> | "
            "<font color='#FF8800'><b>Orange:</b> 15-30% off target</font> | "
            "<font color='#CC0000'><b>Red:</b> &gt;30% off target</font>"
        )
        status_key = Paragraph(status_key_text, self.styles['TrendKey'])
        self.story.append(status_key)
        self.story.append(Spacer(1, 12))
    
    def _get_simple_trend(self, actual_hours: float, expected_hours: float) -> str:
        """Get a simple trend indicator based on current performance.
        
        This is a placeholder - in a full implementation, this would use
        historical data to calculate actual trends.
        
        Args:
            actual_hours: Hours logged this week
            expected_hours: Expected hours per week
            
        Returns:
            Trend indicator
        """
        if expected_hours <= 0:
            return '→'
        
        percentage = (actual_hours / expected_hours) * 100
        
        if percentage > 115:
            return '↑'  # Above expectations
        elif percentage < 85:
            return '↓'  # Below expectations  
        else:
            return '→'  # Meeting expectations
    
    def _add_team_time_distribution(self, report: WeeklyReport, expected_hours: float) -> None:
        """Add team time distribution table with expected vs actual hours.
        
        Args:
            report: Weekly report with team data
            expected_hours: Expected hours per student per week
        """
        dist_title = Paragraph("Team Time Distribution", self.styles['Heading4'])
        self.story.append(dist_title)
        self.story.append(Spacer(1, 6))
        
        # Calculate team expectations
        expected_team_hours = expected_hours * report.num_participants
        actual_team_hours = report.total_hours
        
        # Get performance color and status
        if expected_team_hours > 0:
            team_percentage = (actual_team_hours / expected_team_hours) * 100
            color_hex, status_text = get_hours_status_color(actual_team_hours, expected_team_hours)
        else:
            team_percentage = 100
            color_hex = '#000000'
            status_text = 'No expectations set'
        
        # Create distribution table
        table_data = [
            ["Metric", "Value", "Status"]
        ]
        
        # Team totals row
        actual_para = Paragraph(f'<b>{actual_team_hours:.1f}h</b>', ParagraphStyle(
            'ActualHours', parent=self.styles['Normal'], fontSize=9,
            textColor=colors.HexColor(color_hex), alignment=1
        ))
        
        status_para = Paragraph(status_text, ParagraphStyle(
            'TeamStatus', parent=self.styles['Normal'], fontSize=9,
            textColor=colors.HexColor(color_hex), alignment=0
        ))
        
        table_data.append(["Total Team Hours", actual_para, status_para])
        
        # Expected hours row
        table_data.append([
            "Expected Team Hours", 
            f"{expected_team_hours:.1f}h", 
            f"{report.num_participants} × {expected_hours:.1f}h"
        ])
        
        # Average per person
        avg_actual = actual_team_hours / report.num_participants if report.num_participants > 0 else 0
        avg_color = get_hours_status_color(avg_actual, expected_hours)[0]
        
        avg_para = Paragraph(f'<b>{avg_actual:.1f}h</b>', ParagraphStyle(
            'AvgHours', parent=self.styles['Normal'], fontSize=9,
            textColor=colors.HexColor(avg_color), alignment=1
        ))
        
        table_data.append(["Average per Person", avg_para, f"Target: {expected_hours:.1f}h"])
        
        # Performance summary
        if expected_team_hours > 0:
            perf_indicator = '↑' if team_percentage > 115 else '↓' if team_percentage < 85 else '→'
            table_data.append([
                "Team Performance", 
                f"{team_percentage:.0f}% of target", 
                perf_indicator
            ])
        
        # Create table
        dist_table = Table(table_data, colWidths=[2.2*inch, 1.5*inch, 2.3*inch])
        dist_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6f3ff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),     # Metric names left-aligned
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),   # Values centered
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),     # Status left-aligned
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        
        self.story.append(dist_table)
        self.story.append(Spacer(1, 6))
        
        # Add team distribution key
        team_key_text = (
            f"<b>Team Target:</b> {expected_team_hours:.1f}h ({report.num_participants} members × {expected_hours:.1f}h each) | "
            "Colors indicate team performance vs. expectations"
        )
        team_key = Paragraph(team_key_text, self.styles['TrendKey'])
        self.story.append(team_key)
        self.story.append(Spacer(1, 12))
    
    def _is_most_recent_week(self, report: WeeklyReport, all_entries: list[TimeEntry]) -> bool:
        """Check if this report is for the most recent week.
        
        Args:
            report: Current weekly report
            all_entries: All time entries
            
        Returns:
            True if this is the most recent week
        """
        # Get all unique weeks from all entries
        all_weeks = set(entry.week_start for entry in all_entries)
        if not all_weeks:
            return True
        
        most_recent_week = max(all_weeks)
        return report.week_start == most_recent_week
    
    def _add_individual_trend_chart(self, user: str, team: str, all_entries: list[TimeEntry]) -> None:
        """Add individual trend chart for a user.
        
        Args:
            user: Username
            team: Team name
            all_entries: All time entries for historical data
        """
        # Get historical data for this user
        historical_data = get_user_historical_data(all_entries, user, team)
        
        if not historical_data['user_weekly']:
            return  # Skip if no data
        
        # Create trend chart
        trend_chart = create_individual_trend_chart(
            user,
            historical_data['user_weekly'],
            historical_data['team_avg_weekly'],
            historical_data['all_teams_avg_weekly']
        )
        
        # Convert to bytes and add to PDF
        trend_bytes = figure_to_bytes(trend_chart).getvalue()
        
        # Add trend chart title and chart
        trend_title = Paragraph(f"{user} - Weekly Hours Trend", self.styles['Heading4'])
        self.story.append(trend_title)
        self.story.append(Spacer(1, 6))
        
        try:
            trend_img = Image(BytesIO(trend_bytes), width=6*inch, height=3.6*inch)
            self.story.append(trend_img)
        except Exception as e:
            print(f"Warning: Could not add trend chart for {user}: {e}")
            error_para = Paragraph("Trend chart could not be generated", self.styles['Normal'])
            self.story.append(error_para)
        
        self.story.append(Spacer(1, 12))
    
    def _add_team_comparison_chart(self, team: str, all_entries: list[TimeEntry]) -> None:
        """Add team comparison chart.
        
        Args:
            team: Current team name
            all_entries: All time entries for historical data
        """
        # Get all teams historical data
        all_teams_data = get_all_teams_historical_data(all_entries)
        
        if not all_teams_data:
            return  # Skip if no data
        
        # Create comparison chart
        comparison_chart = create_team_comparison_chart(team, all_teams_data)
        
        # Convert to bytes and add to PDF
        comparison_bytes = figure_to_bytes(comparison_chart).getvalue()
        
        # Add comparison chart title and chart
        comparison_title = Paragraph("Team Performance Comparison", self.styles['Heading4'])
        self.story.append(comparison_title)
        self.story.append(Spacer(1, 6))
        
        try:
            comparison_img = Image(BytesIO(comparison_bytes), width=7*inch, height=4.2*inch)
            self.story.append(comparison_img)
        except Exception as e:
            print(f"Warning: Could not add team comparison chart: {e}")
            error_para = Paragraph("Team comparison chart could not be generated", self.styles['Normal'])
            self.story.append(error_para)
        
        self.story.append(Spacer(1, 12))
    
    def add_weekly_report(self, report: WeeklyReport, entries: list[TimeEntry], all_entries: list[TimeEntry], expected_hours: float = 0.0) -> None:
        """Add a weekly report section to the PDF.
        
        Args:
            report: WeeklyReport object with summary data
            entries: List of time entries for this week and team
            all_entries: List of all time entries (for historical trend analysis)
            expected_hours: Expected hours per student per week
        """
        # Team and week header
        team_title = Paragraph(f"Team: {report.team}", self.styles['TeamTitle'])
        week_range = format_week_range(report.week_start)
        week_title = Paragraph(f"Week of {week_range}", self.styles['WeekTitle'])
        
        self.story.append(team_title)
        self.story.append(week_title)
        self.story.append(Spacer(1, 12))
        
        # Summary statistics
        summary_text = f"""
        <b>Team Summary:</b><br/>
        • Total Hours: {report.total_hours:.1f}h<br/>
        • Participants: {report.num_participants}<br/>
        • Average Hours per Person: {report.avg_hours_per_person:.1f}h
        """.strip()
        
        summary_para = Paragraph(summary_text, self.styles['Summary'])
        self.story.append(summary_para)
        self.story.append(Spacer(1, 12))
        
        # Add trend analysis if available
        if report.activity_trends:
            self._add_trend_table("Activity Trends", report.team_activities, report.activity_trends)
        
        if report.category_trends:
            self._add_trend_table("Category Trends", report.team_categories, report.category_trends)
        
        # Generate and add charts
        user_charts = generate_user_charts_for_week(entries)
        team_category_chart, team_activity_chart = generate_team_charts_for_week(entries, report.team)
        
        # Add individual charts with hours status
        self.story.append(Spacer(1, 20))
        individual_title = Paragraph("Individual Time Distribution", self.styles['Heading3'])
        self.story.append(individual_title)
        self.story.append(Spacer(1, 12))
        
        # Add student hours status section
        if expected_hours > 0:
            self._add_student_hours_status(report, expected_hours)
        
        # Only add trend charts for the most recent week
        is_most_recent_week = self._is_most_recent_week(report, all_entries)
        
        for user, (category_bytes, activity_bytes) in user_charts.items():
            self._add_user_charts(user, category_bytes, activity_bytes)
            
            # Add individual trend chart only for most recent week
            if is_most_recent_week:
                self._add_individual_trend_chart(user, report.team, all_entries)
        
        # Add team charts and distribution table
        self.story.append(Spacer(1, 20))
        team_title_charts = Paragraph(f"Team {report.team} - Combined Time Distribution", self.styles['Heading3'])
        self.story.append(team_title_charts)
        self.story.append(Spacer(1, 12))
        
        # Add team time distribution status
        if expected_hours > 0:
            self._add_team_time_distribution(report, expected_hours)
        
        self._add_team_charts(team_category_chart, team_activity_chart)
        
        # Add team comparison chart only for most recent week
        if is_most_recent_week:
            self._add_team_comparison_chart(report.team, all_entries)
        
        # Page break after each weekly report
        self.story.append(PageBreak())
    
    def _add_trend_table(self, title: str, data: dict[str, float], trends: dict[str, str]) -> None:
        """Add a trend analysis table.
        
        Args:
            title: Table title
            data: Current week's data (activity/category -> hours)
            trends: Trend indicators (activity/category -> indicator)
        """
        trend_title = Paragraph(title, self.styles['Heading4'])
        self.story.append(trend_title)
        self.story.append(Spacer(1, 6))
        
        # Create table data
        table_data = [["Activity/Category", "Hours", "Trend"]]
        
        # Sort by hours (descending)
        sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
        
        for item, hours in sorted_items:
            trend_indicator = trends.get(item, '')
            table_data.append([item, f"{hours:.1f}h", trend_indicator])
        
        # Create table
        trend_table = Table(table_data, colWidths=[3*inch, 1*inch, 0.5*inch])
        trend_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6f2ff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),  # Center align hours and trends
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        self.story.append(trend_table)
        self.story.append(Spacer(1, 6))
        
        # Add trend key
        trend_key_text = "<b>Trend Key:</b> ↑ Increased | ↓ Decreased | → No Change | ★ New Activity/Category"
        trend_key = Paragraph(trend_key_text, self.styles['TrendKey'])
        self.story.append(trend_key)
        self.story.append(Spacer(1, 12))
    
    def _add_user_charts(self, user: str, category_bytes: bytes, activity_bytes: bytes) -> None:
        """Add individual user charts to the PDF.
        
        Args:
            user: Username
            category_bytes: Category chart as PNG bytes
            activity_bytes: Activity chart as PNG bytes
        """
        user_title = Paragraph(f"<b>{user}</b>", self.styles['Heading4'])
        self.story.append(user_title)
        self.story.append(Spacer(1, 6))
        
        # Add charts side by side if possible, or stacked if too wide
        try:
            category_img = Image(BytesIO(category_bytes), width=3.5*inch, height=2.6*inch)
            activity_img = Image(BytesIO(activity_bytes), width=3.5*inch, height=2.6*inch)
            
            # Create a table to place images side by side
            chart_table = Table([[category_img, activity_img]], colWidths=[3.7*inch, 3.7*inch])
            chart_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            self.story.append(chart_table)
            
        except Exception as e:
            # Fallback: add charts vertically
            print(f"Warning: Could not create side-by-side charts for {user}: {e}")
            
            category_img = Image(BytesIO(category_bytes), width=4*inch, height=3*inch)
            activity_img = Image(BytesIO(activity_bytes), width=4*inch, height=3*inch)
            
            self.story.append(category_img)
            self.story.append(Spacer(1, 6))
            self.story.append(activity_img)
        
        self.story.append(Spacer(1, 12))
    
    def _add_team_charts(self, category_bytes: bytes, activity_bytes: bytes) -> None:
        """Add team charts to the PDF.
        
        Args:
            category_bytes: Team category chart as PNG bytes
            activity_bytes: Team activity chart as PNG bytes
        """
        try:
            category_img = Image(BytesIO(category_bytes), width=3.5*inch, height=2.6*inch)
            activity_img = Image(BytesIO(activity_bytes), width=3.5*inch, height=2.6*inch)
            
            # Create a table to place images side by side
            chart_table = Table([[category_img, activity_img]], colWidths=[3.7*inch, 3.7*inch])
            chart_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            self.story.append(chart_table)
            
        except Exception as e:
            # Fallback: add charts vertically
            print(f"Warning: Could not create side-by-side team charts: {e}")
            
            category_img = Image(BytesIO(category_bytes), width=4*inch, height=3*inch)
            activity_img = Image(BytesIO(activity_bytes), width=4*inch, height=3*inch)
            
            self.story.append(category_img)
            self.story.append(Spacer(1, 6))
            self.story.append(activity_img)
        
        self.story.append(Spacer(1, 12))
    
    def build_pdf(self) -> None:
        """Build and save the PDF document."""
        try:
            self.doc.build(self.story)
            print(f"PDF report saved to: {self.output_path}")
        except Exception as e:
            print(f"Error building PDF: {e}")
            raise


def generate_pdf_report(entries: list[TimeEntry], output_path: Path, expected_hours: float = 0.0) -> None:
    """Generate a complete PDF report from time entries.
    
    Args:
        entries: List of all time entries
        output_path: Path where PDF should be saved
        expected_hours: Expected hours per student per week
    """
    # Generate weekly reports
    weekly_reports = generate_weekly_reports(entries)
    
    # Group entries by team and week for chart generation
    grouped_data = group_entries_by_team_and_week(entries)
    
    # Initialize PDF generator
    pdf = MentorDashboardPDF(output_path)
    
    # Add title page
    pdf.add_title_page(entries)
    
    # Add weekly reports
    for report in weekly_reports:
        week_entries = grouped_data[report.team][report.week_start]
        pdf.add_weekly_report(report, week_entries, entries, expected_hours)
    
    # Build PDF
    pdf.build_pdf()


def generate_team_split_reports(entries: list[TimeEntry], output_path: Path, expected_hours: float = 0.0) -> dict[str, Path]:
    """Generate separate PDF reports for each team.
    
    Args:
        entries: List of all time entries
        output_path: Base output path (will be modified for each team)
        expected_hours: Expected hours per student per week
        
    Returns:
        Dictionary mapping team names to their output file paths
    """
    # Generate weekly reports
    weekly_reports = generate_weekly_reports(entries)
    
    # Group entries by team and week for chart generation
    grouped_data = group_entries_by_team_and_week(entries)
    
    # Group reports by team
    team_reports: dict[str, list[WeeklyReport]] = {}
    for report in weekly_reports:
        if report.team not in team_reports:
            team_reports[report.team] = []
        team_reports[report.team].append(report)
    
    # Generate file paths for each team
    output_files: dict[str, Path] = {}
    base_name = output_path.stem
    base_dir = output_path.parent
    
    for team in team_reports.keys():
        # Create team-specific filename
        safe_team_name = team.replace(' ', '_').replace('/', '_')
        team_filename = f"{base_name}_{safe_team_name}.pdf"
        team_output_path = base_dir / team_filename
        output_files[team] = team_output_path
    
    # Generate PDF for each team
    for team, reports in team_reports.items():
        team_output_path = output_files[team]
        
        # Filter entries for this team only
        team_entries = [entry for entry in entries if entry.group == team]
        
        # Initialize PDF generator for this team
        pdf = MentorDashboardPDF(team_output_path)
        
        # Add team-specific title page
        pdf._add_team_title_page(team_entries, team)
        
        # Add weekly reports for this team
        for report in reports:
            week_entries = grouped_data[report.team][report.week_start]
            pdf.add_weekly_report(report, week_entries, entries, expected_hours)
        
        # Build PDF
        pdf.build_pdf()
    
    return output_files
