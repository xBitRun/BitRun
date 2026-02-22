/**
 * Tests for AgentPerformanceTable component
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { AgentPerformanceTable } from "@/components/analytics/agent-performance-table";
import type { AgentPerformance } from "@/lib/api/endpoints";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      "agents.columns.name": "Name",
      "agents.columns.status": "Status",
      "agents.columns.totalPnl": "Total P&L",
      "agents.columns.dailyPnl": "Daily P&L",
      "agents.columns.winRate": "Win Rate",
      "agents.columns.trades": "Trades",
      "agents.columns.positions": "Positions",
      "agents.noData": "No agent data available",
      active: "Active",
      paused: "Paused",
      stopped: "Stopped",
      error: "Error",
      warning: "Warning",
      draft: "Draft",
    };
    return translations[key] || key;
  },
}));

const mockAgents: AgentPerformance[] = [
  {
    agent_id: "agent-1",
    agent_name: "Test Agent",
    strategy_id: "strategy-1",
    strategy_name: "Test Strategy",
    strategy_type: "ai",
    account_id: "account-1",
    status: "active",
    total_pnl: 1000.5,
    daily_pnl: 150.25,
    win_rate: 75.5,
    total_trades: 100,
    open_positions: 2,
  },
  {
    agent_id: "agent-2",
    agent_name: "Loss Agent",
    strategy_id: "strategy-2",
    strategy_name: "Grid Strategy",
    strategy_type: "grid",
    account_id: "account-1",
    status: "paused",
    total_pnl: -500.0,
    daily_pnl: -50.0,
    win_rate: 45.0,
    total_trades: 50,
    open_positions: 0,
  },
];

describe("AgentPerformanceTable", () => {
  it("shows loading skeleton when isLoading is true", () => {
    render(<AgentPerformanceTable agents={[]} isLoading />);

    // Should show 3 skeleton rows
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows empty state when no agents", () => {
    render(<AgentPerformanceTable agents={[]} />);

    expect(screen.getByText("No agent data available")).toBeInTheDocument();
  });

  it("renders agent rows", () => {
    render(<AgentPerformanceTable agents={mockAgents} />);

    expect(screen.getByText("Test Agent")).toBeInTheDocument();
    expect(screen.getByText("Loss Agent")).toBeInTheDocument();
    expect(screen.getByText("Test Strategy")).toBeInTheDocument();
    expect(screen.getByText("GRID")).toBeInTheDocument();
    expect(screen.getByText("AI")).toBeInTheDocument();
  });

  it("displays correct status badges", () => {
    render(<AgentPerformanceTable agents={mockAgents} />);

    // Check for status text within badges
    expect(screen.getByText(/Active/)).toBeInTheDocument();
    expect(screen.getByText(/Paused/)).toBeInTheDocument();
  });

  it("formats currency correctly", () => {
    render(<AgentPerformanceTable agents={mockAgents} />);

    // Positive values have + prefix
    expect(screen.getByText(/\+\$1,000\.50/)).toBeInTheDocument();
    expect(screen.getByText(/\+\$150\.25/)).toBeInTheDocument();

    // Negative values have - prefix
    expect(screen.getByText(/-\$500\.00/)).toBeInTheDocument();
    expect(screen.getByText(/-\$50\.00/)).toBeInTheDocument();
  });

  it("formats win rate as percentage", () => {
    render(<AgentPerformanceTable agents={mockAgents} />);

    expect(screen.getByText("75.5%")).toBeInTheDocument();
    expect(screen.getByText("45.0%")).toBeInTheDocument();
  });

  it("displays trade counts", () => {
    render(<AgentPerformanceTable agents={mockAgents} />);

    expect(screen.getByText("100")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
  });

  it("displays open positions", () => {
    render(<AgentPerformanceTable agents={mockAgents} />);

    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("calls onRowClick when row is clicked", () => {
    const onRowClick = jest.fn();
    render(<AgentPerformanceTable agents={mockAgents} onRowClick={onRowClick} />);

    const row = screen.getByText("Test Agent").closest("tr");
    fireEvent.click(row!);

    expect(onRowClick).toHaveBeenCalledWith("agent-1");
  });

  it("applies custom className", () => {
    render(<AgentPerformanceTable agents={mockAgents} className="custom-table" />);

    const table = screen.getByRole("table");
    expect(table).toHaveClass("custom-table");
  });

  it("renders column headers", () => {
    render(<AgentPerformanceTable agents={mockAgents} />);

    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Total P&L")).toBeInTheDocument();
    expect(screen.getByText("Daily P&L")).toBeInTheDocument();
    expect(screen.getByText("Win Rate")).toBeInTheDocument();
    expect(screen.getByText("Trades")).toBeInTheDocument();
    expect(screen.getByText("Positions")).toBeInTheDocument();
  });

  it("handles zero P&L correctly", () => {
    const agentsWithZero: AgentPerformance[] = [
      {
        ...mockAgents[0],
        total_pnl: 0,
        daily_pnl: 0,
      },
    ];

    render(<AgentPerformanceTable agents={agentsWithZero} />);

    // Zero P&L should show $0.00 (appears multiple times for total and daily)
    const zeroValues = screen.getAllByText(/\$0\.00/);
    expect(zeroValues.length).toBeGreaterThanOrEqual(2);
  });
});
