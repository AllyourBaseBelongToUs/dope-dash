// Report components
export { ReportGenerator } from './ReportGenerator';
export { ReportHistory } from './ReportHistory';
export { ReportViewer } from './ReportViewer';
export { ScheduleCard } from './ScheduleCard';

// Chart components (legacy)
export {
  SessionTrendChart,
  SpecTrendChart,
  ErrorTrendChart,
  SessionsByStatusChart,
  SessionsByAgentChart,
  ComparisonMetricsChart,
  TopErrorsChart,
  ErrorsBySessionChart,
} from './charts';

// New chart components
export {
  SessionDurationChart,
  EventBreakdownChart,
  TrendChart,
  ComparisonChart,
} from './charts';

// Dialog components
export {
  ReportGenerationDialog,
  ScheduleSettingsDialog,
} from './dialogs';
