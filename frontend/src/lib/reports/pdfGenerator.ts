import type { ReportData } from '@/types/reports';
import { generateMarkdownReport } from './markdownGenerator';
import { generateChartImages } from './chartImageGenerator';
import jsPDF from 'jspdf';
import { format } from 'date-fns';

/**
 * PDF Report Generator
 * Generates PDF reports using jsPDF with chart support
 */

// PDF configuration
const PDF_MARGIN = 20;
const PDF_LINE_HEIGHT = 7;
const PDF_PAGE_HEIGHT = 297; // A4 height in mm
const PDF_PAGE_WIDTH = 210; // A4 width in mm
const PDF_CONTENT_WIDTH = PDF_PAGE_WIDTH - PDF_MARGIN * 2;

/**
 * Colors for PDF elements
 */
const COLORS = {
  primary: [59, 130, 246] as [number, number, number], // Blue
  success: [34, 197, 94] as [number, number, number], // Green
  warning: [251, 191, 36] as [number, number, number], // Yellow
  danger: [239, 68, 68] as [number, number, number], // Red
  text: [30, 41, 59] as [number, number, number], // Slate
  muted: [148, 163, 184] as [number, number, number], // Light slate
  border: [226, 232, 240] as [number, number, number], // Border gray
};

/**
 * Convert markdown-style tables to PDF tables
 */
function addTableToPDF(
  doc: jsPDF,
  headers: string[],
  rows: string[][],
  startY: number
): number {
  let y = startY;
  const colWidths = headers.map(() => PDF_CONTENT_WIDTH / headers.length);
  const rowHeight = 8;

  // Set font for headers
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.setFillColor(...COLORS.primary);
  doc.setTextColor(255, 255, 255);

  // Draw header row
  headers.forEach((header, i) => {
    const x = PDF_MARGIN + colWidths.slice(0, i).reduce((a, b) => a + b, 0);
    doc.rect(x, y, colWidths[i], rowHeight, 'F');
    doc.text(header, x + 2, y + 5);
  });

  y += rowHeight;

  // Draw data rows
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...COLORS.text);

  rows.forEach((row, rowIndex) => {
    // Alternate row background
    if (rowIndex % 2 === 0) {
      doc.setFillColor(...COLORS.border);
      row.forEach((_, i) => {
        const x = PDF_MARGIN + colWidths.slice(0, i).reduce((a, b) => a + b, 0);
        doc.rect(x, y, colWidths[i], rowHeight, 'F');
      });
    }

    row.forEach((cell, i) => {
      const x = PDF_MARGIN + colWidths.slice(0, i).reduce((a, b) => a + b, 0);
      // Truncate text if too long
      const maxWidth = colWidths[i] - 4;
      const text = doc.splitTextToSize(cell, maxWidth)[0];
      doc.text(text, x + 2, y + 5);
    });

    y += rowHeight;
  });

  return y + PDF_MARGIN;
}

/**
 * Add a section header to the PDF
 */
function addSectionHeader(doc: jsPDF, text: string, y: number): number {
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.primary);
  doc.text(text, PDF_MARGIN, y);
  return y + PDF_LINE_HEIGHT;
}

/**
 * Add a subsection header to the PDF
 */
function addSubsectionHeader(doc: jsPDF, text: string, y: number): number {
  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.text);
  doc.text(text, PDF_MARGIN, y);
  return y + PDF_LINE_HEIGHT;
}

/**
 * Add regular text to the PDF
 */
function addText(doc: jsPDF, text: string, y: number): number {
  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...COLORS.text);

  const lines = doc.splitTextToSize(text, PDF_CONTENT_WIDTH);
  lines.forEach((line: string) => {
    if (y > PDF_PAGE_HEIGHT - PDF_MARGIN) {
      doc.addPage();
      y = PDF_MARGIN;
    }
    doc.text(line, PDF_MARGIN, y);
    y += PDF_LINE_HEIGHT;
  });

  return y + PDF_LINE_HEIGHT;
}

/**
 * Add a separator line to the PDF
 */
function addSeparator(doc: jsPDF, y: number): number {
  doc.setDrawColor(...COLORS.border);
  doc.line(PDF_MARGIN, y, PDF_PAGE_WIDTH - PDF_MARGIN, y);
  return y + PDF_LINE_HEIGHT;
}

/**
 * Add metadata to the PDF
 */
function addMetadata(doc: jsPDF, data: ReportData): number {
  let y = PDF_MARGIN;

  // Title
  doc.setFontSize(18);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...COLORS.text);
  doc.text(data.title, PDF_MARGIN, y);
  y += PDF_LINE_HEIGHT * 2;

  // Metadata
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...COLORS.muted);

  doc.text(`Generated: ${format(new Date(data.generatedAt), 'yyyy-MM-dd HH:mm:ss')}`, PDF_MARGIN, y);
  y += PDF_LINE_HEIGHT;

  doc.text(`Type: ${data.type} | Format: ${data.format}`, PDF_MARGIN, y);
  y += PDF_LINE_HEIGHT * 2;

  return y;
}

/**
 * Generate session summary section in PDF
 */
function generateSessionSummaryPDF(data: ReportData, doc: jsPDF, y: number): number {
  if (!data.sessions || data.sessions.length === 0) return y;

  y = addSectionHeader(doc, 'Session Summary', y);
  y = addSeparator(doc, y);

  data.sessions.forEach((session) => {
    // Check for new page
    if (y > PDF_PAGE_HEIGHT - 50) {
      doc.addPage();
      y = PDF_MARGIN;
    }

    y = addSubsectionHeader(doc, `${session.projectName}`, y);

    // Metadata table
    const headers = ['Property', 'Value'];
    const rows = [
      ['Session ID', session.sessionId],
      ['Agent Type', session.agentType],
      ['Status', session.status],
      ['Started', format(new Date(session.startedAt), 'yyyy-MM-dd HH:mm')],
      ['Duration', `${Math.round(session.duration / 60)}m ${session.duration % 60}s`],
    ];

    y = addTableToPDF(doc, headers, rows, y);
    y += PDF_MARGIN;

    // Spec execution
    y = addSubsectionHeader(doc, 'Spec Execution', y);
    const specRows = [
      ['Total', session.totalSpecs.toString()],
      ['Completed', session.completedSpecs.toString()],
      ['Failed', session.failedSpecs.toString()],
      ['Success Rate', `${(session.specSuccessRate * 100).toFixed(1)}%`],
    ];
    y = addTableToPDF(doc, ['Metric', 'Count'], specRows, y);
    y += PDF_MARGIN;

    // Events
    y = addSubsectionHeader(doc, 'Events', y);
    const eventRows = Object.entries(session.eventBreakdown).map(([type, count]) => [
      type,
      count.toString(),
    ]);
    y = addTableToPDF(doc, ['Type', 'Count'], eventRows, y);
    y += PDF_MARGIN;
  });

  return y;
}

/**
 * Generate trends section in PDF
 */
function generateTrendsPDF(data: ReportData, doc: jsPDF, y: number): number {
  if (!data.trends) return y;

  const trends = data.trends;

  y = addSectionHeader(doc, 'Trends Analysis', y);
  y = addSeparator(doc, y);

  // Overview
  y = addSubsectionHeader(doc, 'Overview', y);
  const overviewRows = [
    ['Total Sessions', trends.totalSessions.toString()],
    ['Total Spec Runs', trends.totalSpecRuns.toString()],
    ['Avg Duration', `${Math.round(trends.avgSessionDuration / 60)}m`],
    ['Success Rate', `${(trends.specSuccessRate * 100).toFixed(1)}%`],
  ];
  y = addTableToPDF(doc, ['Metric', 'Value'], overviewRows, y);
  y += PDF_MARGIN;

  // Session status
  y = addSubsectionHeader(doc, 'Sessions by Status', y);
  const statusRows = Object.entries(trends.sessionsByStatus).map(([status, count]) => [
    status,
    count.toString(),
  ]);
  y = addTableToPDF(doc, ['Status', 'Count'], statusRows, y);
  y += PDF_MARGIN;

  // Agent types
  y = addSubsectionHeader(doc, 'Sessions by Agent', y);
  const agentRows = Object.entries(trends.sessionsByAgent).map(([agent, count]) => [
    agent,
    count.toString(),
  ]);
  y = addTableToPDF(doc, ['Agent', 'Count'], agentRows, y);

  return y;
}

/**
 * Generate comparison section in PDF
 */
function generateComparisonPDF(data: ReportData, doc: jsPDF, y: number): number {
  if (!data.comparison) return y;

  const { sessions, metrics } = data.comparison;

  y = addSectionHeader(doc, 'Session Comparison', y);
  y = addSeparator(doc, y);

  // Overview metrics
  y = addSubsectionHeader(doc, 'Overview', y);
  const overviewRows = [
    ['Sessions Compared', metrics.totalSessions.toString()],
    ['Avg Duration', `${Math.round(metrics.avgDuration / 60)}m`],
    ['Avg Success Rate', `${(metrics.avgSpecSuccessRate * 100).toFixed(1)}%`],
    ['Total Specs', metrics.totalSpecs.toString()],
  ];
  y = addTableToPDF(doc, ['Metric', 'Value'], overviewRows, y);
  y += PDF_MARGIN;

  // Highlights
  y = addSubsectionHeader(doc, 'Performance Highlights', y);
  const highlightRows = [
    ['Fastest', metrics.fastestSession?.sessionId.slice(0, 12) || 'N/A'],
    ['Slowest', metrics.slowestSession?.sessionId.slice(0, 12) || 'N/A'],
    ['Best Success Rate', `${(metrics.highestSuccessRate?.rate || 0).toFixed(1)}%`],
    ['Worst Success Rate', `${(metrics.lowestSuccessRate?.rate || 0).toFixed(1)}%`],
  ];
  y = addTableToPDF(doc, ['Category', 'Session'], highlightRows, y);
  y += PDF_MARGIN;

  // Session details
  sessions.forEach((session) => {
    if (y > PDF_PAGE_HEIGHT - 40) {
      doc.addPage();
      y = PDF_MARGIN;
    }

    y = addSubsectionHeader(doc, session.projectName, y);
    const sessionRows = [
      ['Status', session.status],
      ['Duration', `${Math.round(session.duration / 60)}m`],
      ['Specs', `${session.completedSpecs}/${session.totalSpecs}`],
      ['Success Rate', `${(session.specSuccessRate * 100).toFixed(1)}%`],
    ];
    y = addTableToPDF(doc, ['Property', 'Value'], sessionRows, y);
    y += PDF_MARGIN;
  });

  return y;
}

/**
 * Generate error analysis section in PDF
 */
function generateErrorAnalysisPDF(data: ReportData, doc: jsPDF, y: number): number {
  if (!data.errorAnalysis) return y;

  const errorAnalysis = data.errorAnalysis;

  y = addSectionHeader(doc, 'Error Analysis', y);
  y = addSeparator(doc, y);

  // Overview
  y = addSubsectionHeader(doc, 'Overview', y);
  const overviewRows = [
    ['Total Errors', errorAnalysis.totalErrors.toString()],
    ['Unique Types', Object.keys(errorAnalysis.errorFrequency).length.toString()],
  ];
  y = addTableToPDF(doc, ['Metric', 'Value'], overviewRows, y);
  y += PDF_MARGIN;

  // Top errors
  y = addSubsectionHeader(doc, 'Top Errors', y);
  const errorRows = errorAnalysis.topErrors.slice(0, 10).map((e, i) => [
    `#${i + 1}`,
    e.message.slice(0, 40) + (e.message.length > 40 ? '...' : ''),
    e.count.toString(),
  ]);
  y = addTableToPDF(doc, ['#', 'Error', 'Count'], errorRows, y);
  y += PDF_MARGIN;

  // Errors by session
  y = addSubsectionHeader(doc, 'Errors by Session', y);
  const sessionRows = errorAnalysis.errorsBySession.slice(0, 15).map((s) => [
    s.sessionId.slice(0, 10),
    s.errorCount.toString(),
    s.mostRecentError.slice(0, 30) + (s.mostRecentError.length > 30 ? '...' : ''),
  ]);
  y = addTableToPDF(doc, ['Session', 'Count', 'Error'], sessionRows, y);

  return y;
}

/**
 * Add chart images to PDF
 */
async function addChartsToPDF(doc: jsPDF, data: ReportData, startY: number): Promise<number> {
  let y = startY;

  try {
    const charts = await generateChartImages(data);

    if (charts.length === 0) {
      return y;
    }

    // Add charts section
    y = addSectionHeader(doc, 'Charts & Visualizations', y);
    y = addSeparator(doc, y);

    for (const chart of charts) {
      // Check if we need a new page
      if (y > PDF_PAGE_HEIGHT - 80) {
        doc.addPage();
        y = PDF_MARGIN;
      }

      // Add chart title
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(...COLORS.text);
      doc.text(chart.title, PDF_MARGIN, y);
      y += PDF_LINE_HEIGHT;

      // Calculate image dimensions to fit page width
      const maxWidth = PDF_CONTENT_WIDTH;
      const scaleFactor = maxWidth / chart.width;
      const imgWidth = maxWidth;
      const imgHeight = chart.height * scaleFactor;

      // Add chart image
      try {
        doc.addImage(chart.dataUrl, 'SVG', PDF_MARGIN, y, imgWidth, imgHeight);
        y += imgHeight + PDF_MARGIN;
      } catch (imgError) {
        // If SVG fails, the chart might be in a different format
        console.warn('Failed to add chart image:', imgError);
        y += 20; // Add space anyway
      }
    }
  } catch (error) {
    console.warn('Failed to generate charts for PDF:', error);
  }

  return y;
}

/**
 * Main function to generate PDF report
 */
export async function generatePDFReport(data: ReportData): Promise<string> {
  // Create PDF document
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  // Add metadata
  let y = addMetadata(doc, data);

  // Add sections based on report type
  if (data.sessions && data.sessions.length > 0) {
    y = generateSessionSummaryPDF(data, doc, y);
  }

  if (data.trends) {
    if (y > PDF_PAGE_HEIGHT - 50) {
      doc.addPage();
      y = PDF_MARGIN;
    }
    y = generateTrendsPDF(data, doc, y);
  }

  if (data.comparison) {
    if (y > PDF_PAGE_HEIGHT - 50) {
      doc.addPage();
      y = PDF_MARGIN;
    }
    y = generateComparisonPDF(data, doc, y);
  }

  if (data.errorAnalysis) {
    if (y > PDF_PAGE_HEIGHT - 50) {
      doc.addPage();
      y = PDF_MARGIN;
    }
    y = generateErrorAnalysisPDF(data, doc, y);
  }

  // Add charts
  if (y > PDF_PAGE_HEIGHT - 80) {
    doc.addPage();
    y = PDF_MARGIN;
  }
  y = await addChartsToPDF(doc, data, y);

  // Add footer
  const totalPages = (doc as any).internal.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...COLORS.muted);
    doc.text(
      `Generated by Dope Dash | Page ${i} of ${totalPages}`,
      PDF_MARGIN,
      PDF_PAGE_HEIGHT - 10
    );
  }

  // Generate PDF as base64 string
  return doc.output('datauristring').split(',')[1] || '';
}
