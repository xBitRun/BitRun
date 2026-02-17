/**
 * Agent Hooks
 *
 * SWR hooks for agent (execution instance) data fetching and mutations.
 * Agent = Strategy + AI Model + Account/Mock.
 */

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { agentsApi, ApiError } from "@/lib/api";
import type {
  AgentResponse,
  AgentPositionResponse,
  AgentAccountStateResponse,
  CreateAgentRequest,
  UpdateAgentRequest,
} from "@/lib/api";
import type { AgentStatus, StrategyType } from "@/types";

// Keys
const AGENTS_KEY = "/agents";
const agentKey = (id: string) => `/agents/${id}`;
const agentPositionsKey = (id: string) => `/agents/${id}/positions`;

/**
 * Fetch all agents.
 * Treats 404 as empty list (graceful degradation when backend route is unavailable).
 */
export function useAgents(params?: {
  status_filter?: AgentStatus;
  strategy_type?: StrategyType;
}) {
  const key = params ? [AGENTS_KEY, params] : AGENTS_KEY;
  const swr = useSWR<AgentResponse[]>(
    key,
    async () => {
      try {
        return await agentsApi.list(params);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          return [];
        }
        throw err;
      }
    },
    {
      revalidateOnFocus: false,
      dedupingInterval: 5000,
    },
  );
  return {
    ...swr,
    agents: swr.data ?? [],
    refresh: swr.mutate,
  };
}

/**
 * Fetch single agent
 */
export function useAgent(id: string | null) {
  return useSWR<AgentResponse>(
    id ? agentKey(id) : null,
    () => agentsApi.get(id!),
    {
      revalidateOnFocus: false,
    },
  );
}

/**
 * Create agent mutation
 */
export function useCreateAgent() {
  return useSWRMutation<AgentResponse, Error, string, CreateAgentRequest>(
    AGENTS_KEY,
    async (_, { arg }) => {
      return agentsApi.create(arg);
    },
  );
}

/**
 * Update agent mutation
 */
export function useUpdateAgent(id: string) {
  return useSWRMutation<AgentResponse, Error, string, UpdateAgentRequest>(
    agentKey(id),
    async (_, { arg }) => {
      return agentsApi.update(id, arg);
    },
  );
}

/**
 * Delete agent mutation
 */
export function useDeleteAgent(id: string) {
  return useSWRMutation<void, Error, string>(agentKey(id), async () => {
    return agentsApi.delete(id);
  });
}

/**
 * Update agent status mutation (start/pause/stop)
 */
export function useUpdateAgentStatus(id: string) {
  return useSWRMutation<AgentResponse, Error, string, AgentStatus>(
    agentKey(id),
    async (_, { arg }) => {
      return agentsApi.updateStatus(id, arg);
    },
  );
}

/**
 * Trigger agent execution manually
 */
export function useTriggerAgent(id: string) {
  return useSWRMutation(agentKey(id), async () => {
    return agentsApi.trigger(id);
  });
}

/**
 * Fetch agent positions (isolated per-agent)
 */
export function useAgentPositions(agentId: string | null) {
  return useSWR<AgentPositionResponse[]>(
    agentId ? agentPositionsKey(agentId) : null,
    () => agentsApi.getPositions(agentId!),
    {
      revalidateOnFocus: false,
      refreshInterval: 30000, // refresh every 30s for positions
    },
  );
}

/**
 * Fetch agent account state (equity, balance, pnl)
 */
const agentAccountStateKey = (id: string) => `/agents/${id}/account-state`;

export function useAgentAccountState(agentId: string | null) {
  return useSWR<AgentAccountStateResponse>(
    agentId ? agentAccountStateKey(agentId) : null,
    () => agentsApi.getAccountState(agentId!),
    {
      revalidateOnFocus: false,
      refreshInterval: 30000, // refresh every 30s
    },
  );
}

/**
 * Get count of active agents
 */
export function useActiveAgentsCount() {
  const { agents } = useAgents();
  return agents.filter((a) => a.status === "active").length;
}
