import type { ErrorEvent, QueryFilters } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ErrorExportData {
  headers: string[];
  rows: string[][];
  total_errors: number;
}

/**
 * Fetch errors from the query API with optional filters
 */
export async function fetchErrors(filters: QueryFilters = {}): Promise<ErrorExportData> {
  const params = new URLSearchParams();

  if (filters.session_id) params.append('session_id', filters.session_id);
  if (filters.event_type) params.append('event_type', filters.event_type);
  if (filters.start_date) params.append('start_date', filters.start_date);
  if (filters.end_date) params.append('end_date', filters.end_date);
  if (filters.limit) params.append('limit', filters.limit.toString());
  if (filters.offset !== undefined) params.append('offset', filters.offset.toString());

  const response = await fetch(`${API_BASE_URL}/api/query/errors/export?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch errors: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Convert error export data to CSV string
 */
export function errorsToCSV(data: ErrorExportData): string {
  const { headers, rows } = data;

  // Escape CSV values
  const escapeCSV = (value: string): string => {
    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
      return `"${value.replace(/"/g, '""')}"`;
    }
    return value;
  };

  // Build CSV content
  const csvRows: string[] = [];

  // Add headers
  csvRows.push(headers.map(escapeCSV).join(','));

  // Add data rows
  for (const row of rows) {
    csvRows.push(row.map(escapeCSV).join(','));
  }

  return csvRows.join('\n');
}

/**
 * Download errors as CSV file
 */
export async function downloadErrorsAsCSV(
  filters: QueryFilters = {},
  filename?: string
): Promise<void> {
  try {
    const data = await fetchErrors(filters);
    const csv = errorsToCSV(data);

    // Generate filename if not provided
    const defaultFilename = `errors_export_${new Date().toISOString().split('T')[0]}.csv`;
    const finalFilename = filename || defaultFilename;

    // Create blob and download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.setAttribute('href', url);
    link.setAttribute('download', finalFilename);
    link.style.display = 'none';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Failed to download errors as CSV:', error);
    throw error;
  }
}

/**
 * Export local ErrorEvent array to CSV
 */
export function exportLocalErrorsToCSV(errors: ErrorEvent[], filename?: string): void {
  const headers = ['Error ID', 'Session ID', 'Event Type', 'Message', 'Stack Trace', 'Created At'];

  const escapeCSV = (value: string): string => {
    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
      return `"${value.replace(/"/g, '""')}"`;
    }
    return value;
  };

  const rows: string[][] = errors.map((error) => [
    error.id,
    error.sessionId,
    error.eventType,
    error.message,
    error.stackTrace || '',
    error.createdAt,
  ]);

  const csvRows: string[] = [
    headers.map(escapeCSV).join(','),
    ...rows.map((row) => row.map(escapeCSV).join(',')),
  ];

  const csv = csvRows.join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');

  const defaultFilename = `local_errors_${new Date().toISOString().split('T')[0]}.csv`;
  const finalFilename = filename || defaultFilename;

  link.setAttribute('href', url);
  link.setAttribute('download', finalFilename);
  link.style.display = 'none';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}
