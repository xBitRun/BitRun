import { render, screen } from "@testing-library/react";

import { ExecutionRecords } from "@/components/decisions/execution-records";
import type { DecisionExecutionResult } from "@/lib/api";

const labels = {
  title: "Execution Records",
  success: "Success",
  failed: "Failed",
  skipped: "Skipped",
  reason: "Reason",
  orderId: "Order ID",
  filledSize: "Filled Size",
  filledPrice: "Filled Price",
  status: "Status",
  requestedSize: "Requested Size",
  actualSize: "Actual Size",
};

const getActionColor = () => "bg-muted";

describe("ExecutionRecords", () => {
  it("renders nothing for empty records", () => {
    const { container } = render(
      <ExecutionRecords records={[]} labels={labels} getActionColor={getActionColor} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders executed record details", () => {
    const records: DecisionExecutionResult[] = [
      {
        symbol: "BTC",
        action: "open_long",
        executed: true,
        reason: "ok",
        reasoning: "ok",
        requested_size_usd: 100,
        actual_size_usd: 95,
        position_size_usd: 95,
        size_usd: 95,
        order_result: {
          order_id: "OID-1",
          filled_size: 0.002,
          filled_price: 50000,
          status: "filled",
        },
      },
    ];

    render(
      <ExecutionRecords records={records} labels={labels} getActionColor={getActionColor} />,
    );

    expect(screen.getByText("Execution Records")).toBeInTheDocument();
    expect(screen.getByText("Success")).toBeInTheDocument();
    expect(screen.getByText("OID-1")).toBeInTheDocument();
    expect(screen.getByText("0.002")).toBeInTheDocument();
    expect(screen.getByText("$50,000")).toBeInTheDocument();
    expect(screen.getByText("filled")).toBeInTheDocument();
    expect(screen.getByText("$100")).toBeInTheDocument();
    expect(screen.getByText("$95")).toBeInTheDocument();
  });

  it("renders failed reason from order error", () => {
    const records: DecisionExecutionResult[] = [
      {
        symbol: "ETH",
        action: "open_short",
        executed: false,
        reason: "risk_blocked",
        reasoning: "risk_blocked",
        position_size_usd: 0,
        size_usd: 0,
        order_result: {
          error: "Insufficient margin",
        },
      },
    ];

    render(
      <ExecutionRecords records={records} labels={labels} getActionColor={getActionColor} />,
    );

    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getAllByText("Reason:").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Insufficient margin").length).toBeGreaterThan(0);
  });
});
