# Skill-Gen: Multi-Agent Specs Creation Process

**Date:** 2026-02-28
**Type:** Process Documentation
**Purpose:** Capture the workflow for brainstorming and creating specs from code analysis

---

## Overview

This document describes the process used to:
1. Deep-dive into Phase 3 Multi-Agent Support codebase
2. Brainstorm 5 new specs with decision analysis
3. Create detailed implementation specs
4. Generate matrix document for feature decisions

---

## Step 1: Deep-Dive Exploration (Explore Agent)

### Tool Used
```
Agent tool with subagent_type="Explore"
Thoroughness: "very thorough"
```

### Prompt Structure
```markdown
Run a thorough deep-dive exploration focusing on:

## Phase 3: Multi-Agent Support - Current State

Explore these files and identify gaps:
1. Agent Wrappers - backend/app/wrappers/
2. Multi-Agent Coordination
3. Session Reassignment
4. Agent Pool Integration

## Integration Opportunities with New Handoff Service

Our new agent_handoff.py service enables:
- Context preservation during agent transfers
- Tool usage summaries
- File modification tracking
- Pending tasks and decisions capture

## Key Questions to Answer:
1. Current agent wrapper architecture?
2. Multi-agent coordination capabilities?
3. Gap analysis?
4. New spec proposals (3-5)?

Return:
- Current architecture summary
- Identified gaps
- 3-5 concrete spec proposals with titles and brief descriptions
```

### What It Returned
- 18-page detailed analysis of:
  - Agent wrapper architecture (BaseAgentWrapper, RalphWrapper, ClaudeWrapper, etc.)
  - Multi-agent coordination services (AgentDetector, AgentRegistry, AgentPool, AutoScaler)
  - Current implementation status
  - 5 concrete spec proposals with titles and descriptions

---

## Step 2: Brainstorming (superpowers:brainstorming)

### Tool Used
```
Skill tool with skill="brainstorming"
```

### Prompt Structure
```markdown
Topic: Multi-Agent Support Specs for Dope-Dash

Context: We just implemented an Agent Handoff Service. We have 5 proposed new specs:
1. Seamless Handoff Integration
2. Agent Communication Bus
3. Parallel Execution Coordinator
4. Specialist Agent Router
5. Multi-Agent Session Aggregation

Please brainstorm each spec with:
- Technical feasibility considerations
- Potential implementation challenges
- Feature variations/options
- Priority ranking
- Dependencies between specs

Focus on practical implementation that fits the existing codebase architecture.
```

### What It Produced

For each spec, the brainstorming output included:

#### 1. Technical Feasibility Assessment
- HIGH/MEDIUM/LOW rating
- Reasons for rating
- Existing infrastructure that can be leveraged

#### 2. Implementation Challenges
- Specific technical hurdles
- Risk areas
- Complexity factors

#### 3. Feature Variations Table
| Option | Description | Complexity | Pros | Cons |
|--------|-------------|------------|------|------|

#### 4. Recommended Approach
- Clear choice with rationale
- Why this option over others

#### 5. Priority Ranking
- ⭐ star ratings (1-5)
- Position in implementation order
- Dependencies

#### 6. Dependency Graph
ASCII art showing which specs depend on others:
```
    ┌─────────────────────┐
    │   Spec 1: Handoff   │
    └──────────┬──────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
 ┌────────┐ ┌──────┐ ┌──────┐
 │ Spec 5 │ │Spec 2│ │Spec 4│
 └────────┘ └──┬───┘ └──────┘
            │
            ▼
       ┌──────────┐
       │  Spec 3 │
       └──────────┘
```

#### 7. Quick Wins Path
Week-by-week breakdown:
- Week 1-2: Specs 1 + 5
- Week 3-4: Spec 4
- Week 5-6: Spec 2
- Week 7+: Spec 3

---

## Step 3: Matrix Document Creation

### File
`docs/plans/2026-02-28-multi-agent-support-matrix.md`

### Structure

#### Header
```markdown
# Multi-Agent Support - Feature Matrix & Decision Document

Date: 2026-02-28
Status: Proposed
Context: Post-Agent Handoff Service Implementation
Goal: Complete Phase 3 (Multi-Agent Support) to 100%
```

#### Executive Summary
- Current status (85% → 100%)
- Brief overview of 5 proposed specs

#### Feature Decision Matrix
| # | Spec Name | Priority | Complexity | Dependencies | Risk | Duration | Status |

#### Detailed Analysis by Spec
For each spec:
1. Decision (with star rating)
2. Decision Trace (why this decision)
3. Technical Feasibility
4. Implementation Options Considered (table)
5. Chosen Approach (with rationale)
6. Files to Modify/Create
7. Architecture Diagram (ASCII art)

#### Implementation Roadmap
Sprint-by-sprint breakdown with daily tasks

#### Risk Assessment
| Risk | Impact | Probability | Mitigation |

#### Success Criteria
Checklist for each spec

#### Architecture Diagram
Full system architecture showing all layers

---

## Step 4: Individual Spec Creation (writing-plans Skill)

### Tool Used
```
Skill tool with skill="writing-plans"
```

### Prompt Structure
```markdown
Create detailed implementation spec for:

**Spec N: [Spec Name]**

Based on the brainstorming decision (Option X), create a comprehensive implementation spec that includes:

1. Overview and objectives
2. Database schema changes (alembic migration)
3. API changes (endpoint modifications)
4. Frontend changes (components)
5. Data flow diagrams
6. Testing checklist
7. Rollback plan

Output to: docs/specs/XX-[spec-name].md
```

### Spec Document Structure

Each spec follows this template:

#### Header
```markdown
# Spec NN: [Spec Name]

Status: Proposed
Priority: ⭐⭐⭐⭐⭐
Complexity: LOW/MEDIUM/HIGH
Duration: X days/weeks
Parent: Phase 3 (Multi-Agent Support)
Dependencies: None / Spec N
```

#### Overview
- Objective
- Problem Statement (Before/After)
- Success Criteria (checklist)

#### Architecture
- Approach (which option chosen)
- Rationale
- Data Flow Diagram (ASCII)
- Component Diagram (ASCII)

#### Database Schema Changes
- SQL table definitions
- Indexes
- Alembic migration code

#### API Changes
- Modified endpoints
- New request parameters
- New response fields
- Implementation code (Python)

#### Frontend Changes
- Modified components
- New components (TypeScript/React)
- Data flow

#### Testing Checklist
- Unit tests
- Integration tests
- Frontend tests
- Manual testing

#### Rollback Plan
- Database rollback
- Code rollback
- Verification steps

#### Documentation
- API docs
- User docs

---

## Step 5: Option Explanation with ASCII Art

For Spec 5 (Multi-Agent Session Aggregation), created detailed ASCII art comparison:

### Option A: Project Page Only
```
┌────────────────────────────────────────┐
│  Multi-Agent Panel                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Ralph   │ │ Claude  │ │ Cursor  │  │
│  │ (3)     │ │ (2)     │ │ (1)     │  │
│  └─────────┘ └─────────┘ └─────────┘  │
└────────────────────────────────────────┘
Updates: Polling 30s | Realtime: No
```

### Option B: Cross-Project
```
┌────────────────────────────────────────┐
│  Portfolio Overview                    │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │Project 1 │ │Project 2 │ │Project3│ │
│  └──────────┘ └──────────┘ └────────┘ │
└────────────────────────────────────────┘
Updates: Polling | Phase: Phase 2
```

### Option C: Real-Time WebSocket
```
┌────────────────────────────────────────┐
│  Live Monitoring                       │
│  Connection: WEBSOCKET ◉               │
│  Last Update: 23ms ago                 │
│  ┌────────────────────────────────────┐│
│  │ 14:32:01 Ralph STARTED Session    ││
│  │ 14:32:05 Claude PROGRESS 95%      ││
│  │ [auto-scrolling...]               ││
│  └────────────────────────────────────┘│
└────────────────────────────────────────┘
Updates: WebSocket | Realtime: Yes
```

### Explanation Table

| Factor | Polling | WebSocket |
|--------|---------|-----------|
| Data freshness | 30s delay | Instant |
| Change frequency | Slow | Fast |
| Infrastructure | Existing HTTP | New WebSocket |
| Complexity | Low | High |

---

## Key Patterns Used

### 1. Decision Trace Pattern
For every decision, document:
- **What** was decided
- **Why** (rationale)
- **Options considered** (with pros/cons)
- **Dependencies** identified

### 2. ASCII Art for Architecture
Use ASCII art for:
- Data flow diagrams
- Component relationships
- State machines
- UI mockups

### 3. Table-Based Comparisons
Use tables for:
- Option comparisons
- Risk assessment
- API parameter changes
- Testing checklists

### 4. Incremental Validation
- Present spec sections (200-300 words each)
- Ask "does this look right?" between sections
- Be ready to go back and clarify

### 5. YAGNI Principle
- Start simple (manual work items, not AI decomposition)
- Dial up complexity when needed (polling → WebSocket)
- Build on existing infrastructure

---

## File Organization

```
docs/
├── plans/
│   └── 2026-02-28-multi-agent-support-matrix.md    # Main decision doc
├── specs/
│   ├── 12-seamless-handoff-integration.md          # Spec 1 (detailed)
│   ├── 13-agent-communication-bus.md               # Spec 2 (detailed)
│   ├── 14-parallel-execution-coordinator.md        # Spec 3 (detailed)
│   ├── 15-specialist-agent-router.md               # Spec 4 (detailed)
│   └── 16-multi-agent-session-aggregation.md       # Spec 5 (detailed)
└── skills/
    └── multi-agent-brainstorming-skill-gen.md      # This file
```

---

## Time Breakdown

| Step | Duration | Output |
|------|----------|--------|
| Deep-dive exploration | ~3 min | 18-page analysis, 5 spec proposals |
| Brainstorming | ~2 min | Decision analysis, options, priorities |
| Matrix document | ~5 min | Complete decision matrix |
| Spec creation (5 specs) | ~15 min | 5 detailed implementation specs |
| Option explanation | ~3 min | ASCII art comparisons |
| Skill-gen document | ~5 min | This process doc |
| **Total** | **~33 min** | **7 documents, ~50 pages** |

---

## Tools Used

1. **Agent tool (Explore)** - Deep codebase analysis
2. **Skill tool (brainstorming)** - Decision analysis
3. **Write tool** - Document creation
4. **Read tool** - Verify existing code patterns

---

## Success Criteria

The process succeeded when:
- ✅ 5 concrete spec proposals generated
- ✅ Each spec has clear rationale and options
- ✅ Priority ranking with dependencies
- ✅ Implementation roadmap with time estimates
- ✅ Detailed specs ready for implementation
- ✅ Matrix document for reference

---

## What Made This Work

1. **Existing handoff service** - Clear foundation to build on
2. **Deep-dive first** - Understood architecture before proposing
3. **Brainstorming with options** - Considered multiple approaches
4. **ASCII art diagrams** - Made decisions visual
5. **Decision trace** - Documented the "why" behind each choice
6. **Incremental specs** - Each spec stands alone but fits together

---

## Future Improvements

1. **Add cost estimates** to roadmap (engineering hours)
2. **Add metrics** for measuring success
3. **Create alternative roadmaps** (aggressive vs conservative)
4. **Add stakeholder feedback** section to each spec
5. **Create rollback criteria** (when to abandon a spec)

---

**Document Version:** 1.0
**Created:** 2026-02-28
**Author:** Claude (via brainstorming + writing-plans skills)
**Status:** Complete
