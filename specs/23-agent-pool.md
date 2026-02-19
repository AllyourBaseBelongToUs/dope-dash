# Spec: Agent Pool Management

## Status: ✅ IMPLEMENTED

## Objective
Agent pool management with load balancing

## Tasks
1. ~~Create agents table (id, type, status, current_project, capabilities)~~ ✅ DONE
2. ~~Implement agent registration service~~ ✅ DONE
3. ~~Create agent health monitoring~~ ✅ DONE
4. ~~Implement load balancing algorithm (least loaded)~~ ✅ DONE (3-tier: preferred, affinity, least-loaded)
5. ~~Add agent capacity tracking (max concurrent projects)~~ ✅ DONE
6. ~~Create agent assignment service~~ ✅ DONE
7. ~~Implement agent auto-scaling (spin up/down)~~ ✅ DONE
8. ~~Add agent pool view in dashboard~~ ✅ DONE
9. ~~Create agent performance metrics~~ ✅ DONE
10. ~~Implement agent affinity (sticky sessions)~~ ✅ DONE

## Acceptance Criteria
- [x] All agents registered in pool
- [x] Health status updates real-time (30s polling)
- [x] Load balancer distributes projects
- [x] Capacity limits enforced
- [x] Performance metrics visible

## Implementation Notes
- **Status:** IMPLEMENTED
- **Database:** Migration file `008_add_agent_pool_table.py` exists
- **All files created and working**

## Files to Create

### Backend
- `backend/app/models/agent_pool.py` - SQLAlchemy model with Pydantic schemas
- `backend/app/services/agent_pool.py` - Core pool service with load balancing
- `backend/app/services/agent_auto_scaler.py` - Auto-scaling service
- `backend/app/api/agent_pool.py` - REST API endpoints

### Frontend
- `frontend/src/app/agent-pool/page.tsx` - Agent pool management page
- `frontend/src/components/agent-pool/PoolMetrics.tsx` - Metrics dashboard
- `frontend/src/components/agent-pool/AgentCard.tsx` - Individual agent card
- `frontend/src/components/agent-pool/PoolFilters.tsx` - Filter controls
- `frontend/src/components/agent-pool/RegisterAgentDialog.tsx` - Agent registration dialog
- `frontend/src/components/ui/progress.tsx` - Progress bar component (if not exists)
- `frontend/src/store/agentPoolStore.ts` - Zustand state management
- `frontend/src/types/index.ts` - TypeScript types for agent pool

## API Endpoints to Implement

### Pool Management
- `GET /api/agent-pool` - List agents (with filtering)
- `POST /api/agent-pool` - Register agent
- `GET /api/agent-pool/{pool_id}` - Get agent by ID
- `GET /api/agent-pool/agent-id/{agent_id}` - Get by external agent ID
- `PATCH /api/agent-pool/{pool_id}` - Update agent
- `DELETE /api/agent-pool/{pool_id}` - Unregister agent

### Agent Control
- `POST /api/agent-pool/{agent_id}/status` - Set agent status
- `POST /api/agent-pool/{agent_id}/heartbeat` - Update heartbeat
- `POST /api/agent-pool/assign` - Assign agent to project
- `POST /api/agent-pool/{agent_id}/release` - Release agent

### Metrics
- `GET /api/agent-pool/metrics/summary` - Pool metrics
- `GET /api/agent-pool/metrics/health` - Health report

### Auto-Scaling
- `GET /api/agent-pool/scaling/recommendation` - Get scaling recommendation
- `POST /api/agent-pool/scaling/execute` - Execute scaling action
- `GET /api/agent-pool/scaling/history` - Scaling event history
- `GET /api/agent-pool/scaling/policy` - Get scaling policy
- `POST /api/agent-pool/scaling/policy` - Update scaling policy
- `POST /api/agent-pool/scaling/start` - Start auto-scaling monitoring
- `POST /api/agent-pool/scaling/stop` - Stop auto-scaling monitoring

## Dependencies
22-command-history

## End State
Agent pool managed automatically
