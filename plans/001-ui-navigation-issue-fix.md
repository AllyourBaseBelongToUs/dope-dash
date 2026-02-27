# Plan: UI Navigation Issue Fix

**Status:** RESEARCH REQUIRED (not implementation)
**Created:** 2025-02-20
**Type:** Research Plan

## Problem Statement

The dope-dash application appears to lack a consistent navigation system between pages. Currently:
- No sidebar navigation component exists
- Pages (`/`, `/settings`, `/portfolio`, `/projects`, `/reports`, `/quota`, `/retention`, `/agent-pool`) are isolated
- Layout (`frontend/src/app/layout.tsx`) only wraps children without navigation
- Command Palette exists but may not be discoverable

## Research Tasks

### Phase 1: Audit Current Navigation
- [ ] Review all pages in `frontend/src/app/` and document current navigation patterns
- [ ] Check if any navigation components exist but aren't used
- [ ] Document which pages are accessible and how users discover them
- [ ] Identify any broken links or missing routes

### Phase 2: Analyze Requirements
- [ ] Define what navigation elements are needed:
  - Sidebar?
  - Header nav?
  - Breadcrumbs?
  - Footer links?
- [ ] Determine mobile responsiveness requirements
- [ ] Review existing UI components that could be reused (from `@/components/ui/`)

### Phase 3: Research Best Practices
- [ ] Research Next.js App Router navigation patterns (2025)
- [ ] Review shadcn/ui navigation components availability
- [ ] Check if Radix UI primitives exist for navigation
- [ ] Look at similar dashboard layouts for inspiration

### Phase 4: Define Success Criteria
- [ ] Users can navigate between all main sections
- [ ] Current page is highlighted in navigation
- [ ] Navigation is accessible (keyboard, screen reader)
- [ ] Mobile-friendly navigation exists
- [ ] No page reload required for navigation (SPA behavior)

## Files to Research

```
frontend/src/app/layout.tsx          # Root layout
frontend/src/app/page.tsx            # Home page
frontend/src/app/settings/page.tsx   # Settings page
frontend/src/app/portfolio/page.tsx  # Portfolio page
frontend/src/app/projects/page.tsx   # Projects page
frontend/src/app/reports/page.tsx    # Reports page
frontend/src/app/quota/page.tsx      # Quota page
frontend/src/app/retention/page.tsx  # Retention page
frontend/src/app/agent-pool/page.tsx # Agent Pool page
frontend/src/components/CommandPalette.tsx  # Existing command navigation
frontend/src/components/ui/          # Reusable UI components
```

## Questions to Answer

1. Is there an existing navigation component that just needs integration?
2. Should navigation be in a sidebar or top bar?
3. How does the Command Palette fit into navigation strategy?
4. What are the main sections that need navigation items?
5. Are there any accessibility requirements?

## Next Steps (After Research)

1. Design navigation component architecture
2. Create implementation plan
3. Build and test navigation
4. Update all pages to use shared layout

## Notes

- This is a RESEARCH plan, not implementation
- User will implement after reviewing research findings
- Focus on documenting current state and recommended approach
