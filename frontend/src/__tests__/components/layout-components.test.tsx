/**
 * Tests for layout components: CollapsibleCard, FormPageHeader, TipsToggle
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import { CollapsibleCard } from "@/components/layout/collapsible-card";
import { FormPageHeader } from "@/components/layout/form-page-header";
import { TipsToggle } from "@/components/layout/tips-toggle";

// ---- CollapsibleCard ----

describe("CollapsibleCard", () => {
  it("should render title", () => {
    render(
      <CollapsibleCard title="Advanced Settings" open={false} onOpenChange={jest.fn()}>
        <div>Content</div>
      </CollapsibleCard>
    );

    expect(screen.getByText("Advanced Settings")).toBeInTheDocument();
  });

  it("should render description when provided", () => {
    render(
      <CollapsibleCard
        title="Settings"
        description="Configure advanced options"
        open={false}
        onOpenChange={jest.fn()}
      >
        <div>Content</div>
      </CollapsibleCard>
    );

    expect(screen.getByText("Configure advanced options")).toBeInTheDocument();
  });

  it("should render icon when provided", () => {
    render(
      <CollapsibleCard
        title="Settings"
        icon={<span data-testid="settings-icon">⚙️</span>}
        open={false}
        onOpenChange={jest.fn()}
      >
        <div>Content</div>
      </CollapsibleCard>
    );

    expect(screen.getByTestId("settings-icon")).toBeInTheDocument();
  });

  it("should render children when open", () => {
    render(
      <CollapsibleCard title="Settings" open={true} onOpenChange={jest.fn()}>
        <div>Visible Content</div>
      </CollapsibleCard>
    );

    expect(screen.getByText("Visible Content")).toBeInTheDocument();
  });
});

// ---- FormPageHeader ----

describe("FormPageHeader", () => {
  it("should render title and back link", () => {
    render(<FormPageHeader backHref="/agents" title="Create Agent" />);

    expect(screen.getByText("Create Agent")).toBeInTheDocument();
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/agents");
  });

  it("should render subtitle when provided", () => {
    render(
      <FormPageHeader
        backHref="/agents"
        title="Create Agent"
        subtitle="Configure your new trading agent"
      />
    );

    expect(screen.getByText("Configure your new trading agent")).toBeInTheDocument();
  });

  it("should call onSubmit when submit button is clicked", async () => {
    const user = userEvent.setup();
    const handleSubmit = jest.fn();

    render(
      <FormPageHeader
        backHref="/agents"
        title="Create"
        onSubmit={handleSubmit}
        submitLabel="Save"
      />
    );

    const submitButton = screen.getByRole("button", { name: /Save/i });
    await user.click(submitButton);

    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });

  it("should disable submit button when isSubmitting is true", () => {
    render(
      <FormPageHeader
        backHref="/agents"
        title="Create"
        onSubmit={jest.fn()}
        submitLabel="Save"
        isSubmitting={true}
      />
    );

    const submitButton = screen.getByRole("button", { name: /Save/i });
    expect(submitButton).toBeDisabled();
  });
});

// ---- TipsToggle ----

describe("TipsToggle", () => {
  const sampleTips = [
    { title: "Tip 1", description: "First tip description" },
    { title: "Tip 2", description: "Second tip description" },
  ];

  it("should render toggle button with label", () => {
    render(
      <TipsToggle show={false} onToggle={jest.fn()} tips={sampleTips} label="Show Tips" />
    );

    expect(screen.getByText("Show Tips")).toBeInTheDocument();
  });

  it("should call onToggle when button is clicked", async () => {
    const user = userEvent.setup();
    const handleToggle = jest.fn();

    render(
      <TipsToggle show={false} onToggle={handleToggle} tips={sampleTips} />
    );

    await user.click(screen.getByRole("button"));

    expect(handleToggle).toHaveBeenCalledTimes(1);
  });

  it("should display tips content when show is true", () => {
    render(
      <TipsToggle show={true} onToggle={jest.fn()} tips={sampleTips} />
    );

    expect(screen.getByText("Tip 1")).toBeInTheDocument();
    expect(screen.getByText("First tip description")).toBeInTheDocument();
    expect(screen.getByText("Tip 2")).toBeInTheDocument();
    expect(screen.getByText("Second tip description")).toBeInTheDocument();
  });

  it("should not display tips content when show is false", () => {
    render(
      <TipsToggle show={false} onToggle={jest.fn()} tips={sampleTips} />
    );

    expect(screen.queryByText("Tip 1")).not.toBeInTheDocument();
    expect(screen.queryByText("Tip 2")).not.toBeInTheDocument();
  });
});
