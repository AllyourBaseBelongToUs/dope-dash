'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { QuotaDashboard } from '@/components/quota/QuotaDashboard';
import { RateLimitDashboard } from '@/components/quota/RateLimitDashboard';
import { RequestQueueDashboard } from '@/components/quota/RequestQueueDashboard';
import { AlertBanner } from '@/components/quota/AlertBanner';
import { AlertHistory } from '@/components/quota/AlertHistory';
import { AlertConfigPanel } from '@/components/quota/AlertConfigPanel';
import {
  Gauge,
  AlertTriangle,
  ListOrdered,
  Settings,
  Bell,
  History,
} from 'lucide-react';

export default function QuotaPage() {
  const [activeTab, setActiveTab] = useState('usage');

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <nav className="flex items-center space-x-2 text-sm text-muted-foreground mb-2">
            <a href="/" className="hover:text-foreground transition-colors">
              Home
            </a>
            <span>/</span>
            <span className="text-foreground font-medium">Quota Management</span>
          </nav>
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 p-2 rounded-lg">
              <Settings className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Quota Management</h1>
              <p className="text-xs text-muted-foreground">
                Monitor API quotas, rate limits, and request queues
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        {/* Active Alert Banner - Shows at the top */}
        <div className="mb-6">
          <AlertBanner maxHeight={200} />
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-6 lg:w-[750px] mb-6">
            <TabsTrigger value="usage" className="gap-2">
              <Gauge className="h-4 w-4" />
              Usage
            </TabsTrigger>
            <TabsTrigger value="rate-limits" className="gap-2">
              <AlertTriangle className="h-4 w-4" />
              Rate Limits
            </TabsTrigger>
            <TabsTrigger value="queue" className="gap-2">
              <ListOrdered className="h-4 w-4" />
              Queue
            </TabsTrigger>
            <TabsTrigger value="alerts" className="gap-2">
              <Bell className="h-4 w-4" />
              Alerts
            </TabsTrigger>
            <TabsTrigger value="history" className="gap-2">
              <History className="h-4 w-4" />
              History
            </TabsTrigger>
            <TabsTrigger value="settings" className="gap-2">
              <Settings className="h-4 w-4" />
              Settings
            </TabsTrigger>
          </TabsList>

          <TabsContent value="usage" className="space-y-6">
            <QuotaDashboard />
          </TabsContent>

          <TabsContent value="rate-limits" className="space-y-6">
            <RateLimitDashboard />
          </TabsContent>

          <TabsContent value="queue" className="space-y-6">
            <RequestQueueDashboard />
          </TabsContent>

          <TabsContent value="alerts" className="space-y-6">
            <AlertHistory showFilters={true} limit={50} />
          </TabsContent>

          <TabsContent value="history" className="space-y-6">
            <AlertHistory showFilters={true} limit={100} />
          </TabsContent>

          <TabsContent value="settings" className="space-y-6">
            <AlertConfigPanel />
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
