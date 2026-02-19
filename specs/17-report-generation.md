# Spec: Report Generation

## Status: ✅ COMPLETED

## Objective
Automated PDF and Markdown report generation

## Tasks
1. Create report generation service
2. Implement Markdown report template
3. Add session summary to reports
4. Include spec run results in reports
5. Generate charts for metrics (using recharts)
6. Implement PDF export (jsPDF or puppeteer)
7. Add report scheduling (daily/weekly)
8. Create report history view
9. Add report download buttons
10. Store reports in filesystem with retention

## Acceptance Criteria
- [x] Markdown reports generate correctly
- [x] PDF exports include charts
- [x] Scheduled reports run automatically
- [x] Download buttons work
- [x] Old reports cleaned up

## Implementation Notes
- **Status:** FULLY IMPLEMENTED
- **Frontend Libraries:** recharts (charts), jsPDF, html2pdf.js (PDF)
- **Backend Libraries:** weasyprint (PDF generation), markdown2 (Markdown processing), APScheduler (scheduling)
- **Storage:** Filesystem with configurable retention (default 30 days)

### Frontend Components
- `/src/services/reportService.ts` - Report generation API client
- `/src/services/reportScheduleService.ts` - Schedule management client
- `/src/lib/reports/markdownGenerator.ts` - Markdown report templates
- `/src/lib/reports/pdfGenerator.ts` - PDF generation with jsPDF
- `/src/lib/reports/chartImageGenerator.ts` - Chart to image conversion
- `/src/components/reports/ReportHistory.tsx` - History view with download
- `/src/components/reports/ReportGenerator.tsx` - Report generation UI
- `/src/components/reports/ScheduleCard.tsx` - Schedule management UI
- `/src/app/reports/page.tsx` - Reports page

### Backend Implementation
- `/app/api/reports.py` - Full REST API for reports and schedules
- `/app/lib/report_generator.py` - Report generation engine with real data
- `/app/lib/scheduler.py` - APScheduler-based automated scheduling
- `/app/models/report.py` - Database models for reports and schedules

### Features Implemented
1. **Report Types:**
   - Session reports (individual or batch)
   - Trends analysis (30-day periods)
   - Session comparison
   - Error analysis

2. **Export Formats:**
   - Markdown (.md)
   - PDF (.pdf) with embedded charts
   - JSON (.json)
   - HTML (.html)

3. **Scheduling:**
   - Daily, weekly, monthly frequencies
   - Automatic next run calculation
   - Test run functionality
   - Enabled/disabled states

4. **Filesystem Storage:**
   - Configurable reports directory
   - Metadata files (.meta.json)
   - Automatic cleanup based on retention policy
   - File download via API endpoints

5. **Charts & Visualizations:**
   - Session duration charts (bar)
   - Error trends (line)
   - Spec completion trends (bar)
   - Agent type distribution
   - Status breakdown

## Dependencies
16-environment-detection

## End State
Users can generate and download reports ✅
