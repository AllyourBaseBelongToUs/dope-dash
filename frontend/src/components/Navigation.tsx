'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  Activity,
  Server,
  FolderKanban,
  FileText,
  BarChart3,
  Gauge,
  Settings,
  Link2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface NavigationProps {
  sessionCount?: number;
  agentCount?: number;
}

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: number;
}

export function Navigation({ sessionCount = 0, agentCount = 0 }: NavigationProps) {
  const pathname = usePathname();

  const navItems: NavItem[] = [
    {
      label: 'Dashboard',
      href: '/',
      icon: <Activity className="h-4 w-4" />,
      badge: sessionCount > 0 ? sessionCount : undefined,
    },
    {
      label: 'Agent Pool',
      href: '/agent-pool',
      icon: <Server className="h-4 w-4" />,
      badge: agentCount > 0 ? agentCount : undefined,
    },
    {
      label: 'Portfolio',
      href: '/portfolio',
      icon: <FolderKanban className="h-4 w-4" />,
    },
    {
      label: 'Assignment',
      href: '/assignment',
      icon: <Link2 className="h-4 w-4" />,
    },
    {
      label: 'Reports',
      href: '/reports',
      icon: <FileText className="h-4 w-4" />,
    },
    {
      label: 'Analytics',
      href: '/analytics',
      icon: <BarChart3 className="h-4 w-4" />,
    },
    {
      label: 'Quota',
      href: '/quota',
      icon: <Gauge className="h-4 w-4" />,
    },
    {
      label: 'Settings',
      href: '/settings',
      icon: <Settings className="h-4 w-4" />,
    },
  ];

  return (
    <nav className="border-b border-border bg-card/50 backdrop-blur-sm">
      <div className="container mx-auto px-4">
        <div className="flex items-center h-12">
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link key={item.href} href={item.href}>
                  <Button
                    variant={isActive ? 'secondary' : 'ghost'}
                    size="sm"
                    className={cn(
                      'gap-2 text-sm',
                      isActive && 'bg-secondary text-secondary-foreground'
                    )}
                  >
                    {item.icon}
                    <span className="hidden sm:inline">{item.label}</span>
                    {item.badge !== undefined && item.badge > 0 && (
                      <span className="ml-1 px-1.5 py-0.5 text-xs bg-primary text-primary-foreground rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </Button>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
