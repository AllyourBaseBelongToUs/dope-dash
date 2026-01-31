'use client';

import { RetentionDashboard } from '@/components/retention/RetentionDashboard';
import { Database } from 'lucide-react';

export default function RetentionPage() {
  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 p-2 rounded-lg">
              <Database className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Data Retention</h1>
              <p className="text-xs text-muted-foreground">Data lifecycle management & cleanup policies</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        <RetentionDashboard />
      </div>

      {/* Footer */}
      <footer className="border-t border-border mt-8">
        <div className="container mx-auto px-4 py-4">
          <p className="text-xs text-muted-foreground text-center">
            Dope Dash - Data Retention Management
          </p>
        </div>
      </footer>
    </main>
  );
}
