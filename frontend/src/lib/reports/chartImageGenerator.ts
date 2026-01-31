import type { ReportData } from '@/types/reports';

/**
 * Chart Image Generator
 * Generates chart images for inclusion in PDF reports
 */

export interface ChartImageData {
  type: 'session_duration' | 'error_rate' | 'spec_completion' | 'agent_performance';
  title: string;
  dataUrl: string;
  width: number;
  height: number;
}

/**
 * Generate a simple bar chart as SVG data URL
 */
function generateBarChartSVG(
  title: string,
  labels: string[],
  values: number[],
  color: string = '#3b82f6'
): string {
  const maxValue = Math.max(...values);
  const chartHeight = 200;
  const chartWidth = 500;
  const barWidth = Math.min(40, (chartWidth - 60) / values.length - 10);
  const startX = 50;
  const startY = 30;

  // Calculate bar heights
  const bars = values.map((value, index) => {
    const barHeight = maxValue > 0 ? (value / maxValue) * (chartHeight - 40) : 0;
    const x = startX + index * (barWidth + 10);
    const y = startY + (chartHeight - 40) - barHeight;
    return { x, y, width: barWidth, height: barHeight, value, label: labels[index] };
  });

  // Generate SVG
  const svgParts: string[] = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${chartWidth}" height="${chartHeight}" viewBox="0 0 ${chartWidth} ${chartHeight}">`,
    `<style>.title { font: bold 14px sans-serif; fill: #1e293b; } .label { font: 10px sans-serif; fill: #64748b; } .value { font: 10px sans-serif; fill: #3b82f6; }</style>`,
    `<text x="${chartWidth / 2}" y="20" text-anchor="middle" class="title">${title}</text>`,
  ];

  // Add bars
  bars.forEach((bar) => {
    svgParts.push(`<rect x="${bar.x}" y="${bar.y}" width="${bar.width}" height="${bar.height}" fill="${color}" rx="2"/>`);
    svgParts.push(`<text x="${bar.x + bar.width / 2}" y="${bar.y - 5}" text-anchor="middle" class="value">${bar.value}</text>`);
    svgParts.push(`<text x="${bar.x + bar.width / 2}" y="${startY + chartHeight - 35}" text-anchor="middle" class="label">${bar.label.slice(0, 8)}</text>`);
  });

  // Add axis line
  svgParts.push(`<line x1="${startX - 5}" y1="${startY + chartHeight - 40}" x2="${chartWidth - 20}" y2="${startY + chartHeight - 40}" stroke="#cbd5e1" stroke-width="1"/>`);

  svgParts.push('</svg>');

  return svgParts.join('');
}

/**
 * Generate a simple line chart as SVG data URL
 */
function generateLineChartSVG(
  title: string,
  labels: string[],
  values: number[],
  color: string = '#3b82f6'
): string {
  const maxValue = Math.max(...values);
  const minValue = Math.min(...values, 0);
  const chartHeight = 200;
  const chartWidth = 500;
  const startX = 50;
  const startY = 30;
  const graphHeight = chartHeight - 60;

  // Calculate points
  const points = values.map((value, index) => {
    const x = startX + (index / (values.length - 1 || 1)) * (chartWidth - 80);
    const range = maxValue - minValue || 1;
    const normalizedValue = (value - minValue) / range;
    const y = startY + graphHeight - (normalizedValue * graphHeight);
    return { x, y, value, label: labels[index] };
  });

  // Generate SVG
  const svgParts: string[] = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${chartWidth}" height="${chartHeight}" viewBox="0 0 ${chartWidth} ${chartHeight}">`,
    `<style>.title { font: bold 14px sans-serif; fill: #1e293b; } .label { font: 10px sans-serif; fill: #64748b; } .value { font: 10px sans-serif; fill: #3b82f6; }</style>`,
    `<text x="${chartWidth / 2}" y="20" text-anchor="middle" class="title">${title}</text>`,
  ];

  // Add grid lines
  for (let i = 0; i <= 4; i++) {
    const y = startY + (i * graphHeight / 4);
    svgParts.push(`<line x1="${startX}" y1="${y}" x2="${chartWidth - 30}" y2="${y}" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="3,3"/>`);
  }

  // Add line path
  if (points.length > 1) {
    const pathData = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
    svgParts.push(`<path d="${pathData}" fill="none" stroke="${color}" stroke-width="2"/>`);

    // Add dots
    points.forEach((point) => {
      svgParts.push(`<circle cx="${point.x}" cy="${point.y}" r="3" fill="${color}"/>`);
    });
  }

  // Add axis lines
  svgParts.push(`<line x1="${startX}" y1="${startY}" x2="${startX}" y2="${startY + graphHeight}" stroke="#cbd5e1" stroke-width="1"/>`);
  svgParts.push(`<line x1="${startX}" y1="${startY + graphHeight}" x2="${chartWidth - 30}" y2="${startY + graphHeight}" stroke="#cbd5e1" stroke-width="1"/>`);

  svgParts.push('</svg>');

  return svgParts.join('');
}

/**
 * Generate a simple pie chart as SVG data URL
 */
function generatePieChartSVG(
  title: string,
  labels: string[],
  values: number[],
  colors: string[] = ['#3b82f6', '#22c55e', '#ef4444', '#f59e0b', '#8b5cf6']
): string {
  const chartWidth = 300;
  const chartHeight = 200;
  const centerX = 100;
  const centerY = 110;
  const radius = 70;

  const total = values.reduce((sum, v) => sum + v, 0);
  let currentAngle = -Math.PI / 2;

  // Generate SVG
  const svgParts: string[] = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${chartWidth}" height="${chartHeight}" viewBox="0 0 ${chartWidth} ${chartHeight}">`,
    `<style>.title { font: bold 14px sans-serif; fill: #1e293b; } .label { font: 10px sans-serif; fill: #64748b; } .legend { font: 10px sans-serif; fill: #334155; }</style>`,
    `<text x="${centerX}" y="20" text-anchor="middle" class="title">${title}</text>`,
  ];

  // Add pie slices
  values.forEach((value, index) => {
    const sliceAngle = (value / total) * 2 * Math.PI;
    const endAngle = currentAngle + sliceAngle;

    const x1 = centerX + radius * Math.cos(currentAngle);
    const y1 = centerY + radius * Math.sin(currentAngle);
    const x2 = centerX + radius * Math.cos(endAngle);
    const y2 = centerY + radius * Math.sin(endAngle);

    const largeArcFlag = sliceAngle > Math.PI ? 1 : 0;

    svgParts.push(`<path d="M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z" fill="${colors[index % colors.length]}" stroke="#ffffff" stroke-width="1"/>`);

    currentAngle = endAngle;
  });

  // Add legend
  const legendX = 200;
  let legendY = 40;
  values.forEach((value, index) => {
    const percentage = ((value / total) * 100).toFixed(1);
    svgParts.push(`<rect x="${legendX}" y="${legendY}" width="12" height="12" fill="${colors[index % colors.length]}" rx="2"/>`);
    svgParts.push(`<text x="${legendX + 18}" y="${legendY + 10}" class="legend">${labels[index]}: ${percentage}%</text>`);
    legendY += 20;
  });

  svgParts.push('</svg>');

  return svgParts.join('');
}

/**
 * Generate chart images from report data
 */
export async function generateChartImages(data: ReportData): Promise<ChartImageData[]> {
  const charts: ChartImageData[] = [];

  // Session duration chart
  if (data.sessions && data.sessions.length > 0) {
    const sessions = data.sessions
      .slice(0, 10)
      .sort((a, b) => b.duration - a.duration);

    const svg = generateBarChartSVG(
      'Session Duration (minutes)',
      sessions.map((s) => s.projectName.slice(0, 10)),
      sessions.map((s) => Math.round(s.duration / 60)),
      '#3b82f6'
    );

    charts.push({
      type: 'session_duration',
      title: 'Session Duration',
      dataUrl: `data:image/svg+xml;base64,${btoa(svg)}`,
      width: 500,
      height: 200,
    });
  }

  // Error rate chart
  if (data.trends && data.trends.errorTrend && data.trends.errorTrend.length > 0) {
    const errorTrend = data.trends.errorTrend.slice(-10);
    const svg = generateLineChartSVG(
      'Error Trend',
      errorTrend.map((p) => new Date(p.timestamp).toLocaleDateString()),
      errorTrend.map((p) => p.count),
      '#ef4444'
    );

    charts.push({
      type: 'error_rate',
      title: 'Error Rate Trend',
      dataUrl: `data:image/svg+xml;base64,${btoa(svg)}`,
      width: 500,
      height: 200,
    });
  }

  // Spec completion chart
  if (data.trends && data.trends.specTrend && data.trends.specTrend.length > 0) {
    const specTrend = data.trends.specTrend.slice(-10);

    const completedSvg = generateBarChartSVG(
      'Spec Completions',
      specTrend.map((p) => new Date(p.timestamp || '').toLocaleDateString()),
      specTrend.map((p) => p.completed),
      '#22c55e'
    );

    charts.push({
      type: 'spec_completion',
      title: 'Spec Completion',
      dataUrl: `data:image/svg+xml;base64,${btoa(completedSvg)}`,
      width: 500,
      height: 200,
    });
  }

  // Agent performance chart
  if (data.trends && data.trends.sessionsByAgent) {
    const agentLabels = Object.keys(data.trends.sessionsByAgent);
    const agentValues = Object.values(data.trends.sessionsByAgent) as number[];

    if (agentLabels.length > 0) {
      const svg = generatePieChartSVG(
        'Sessions by Agent',
        agentLabels,
        agentValues,
        ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']
      );

      charts.push({
        type: 'agent_performance',
        title: 'Agent Performance',
        dataUrl: `data:image/svg+xml;base64,${btoa(svg)}`,
        width: 300,
        height: 200,
      });
    }
  }

  return charts;
}

/**
 * Convert SVG data URL to a format that can be embedded in PDF
 */
export function svgToPdfCompatible(dataUrl: string): string {
  // jsPDF can handle base64 images, so we just return the data URL as-is
  // The SVG will be converted by the browser when drawn to canvas
  return dataUrl;
}
