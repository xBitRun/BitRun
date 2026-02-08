/**
 * Tests for list page components: ListPageEmpty, ListPageError, ListPageSkeleton
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { Bot, Plus } from "lucide-react";

import { ListPageEmpty } from "@/components/list-page/list-page-empty";
import { ListPageError } from "@/components/list-page/list-page-error";
import { ListPageSkeleton } from "@/components/list-page/list-page-skeleton";

// ---- ListPageEmpty ----

describe("ListPageEmpty", () => {
  const defaultProps = {
    icon: Bot,
    title: "No Agents Found",
    description: "Create your first AI agent to get started.",
    actionLabel: "Create Agent",
    actionHref: "/agents/create",
  };

  it("should render title and description", () => {
    render(<ListPageEmpty {...defaultProps} />);

    expect(screen.getByText("No Agents Found")).toBeInTheDocument();
    expect(
      screen.getByText("Create your first AI agent to get started.")
    ).toBeInTheDocument();
  });

  it("should render action button with correct link", () => {
    render(<ListPageEmpty {...defaultProps} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/agents/create");
    expect(screen.getByText("Create Agent")).toBeInTheDocument();
  });

  it("should render action icon when provided", () => {
    render(<ListPageEmpty {...defaultProps} actionIcon={Plus} />);

    // The button still renders with the label
    expect(screen.getByText("Create Agent")).toBeInTheDocument();
  });
});

// ---- ListPageError ----

describe("ListPageError", () => {
  it("should render error message", () => {
    render(
      <ListPageError message="Failed to load agents" onRetry={jest.fn()} />
    );

    expect(screen.getByText("Failed to load agents")).toBeInTheDocument();
  });

  it("should render retry button with default translated label", () => {
    render(<ListPageError message="Error" onRetry={jest.fn()} />);

    // useTranslations mock returns the key, so label is "retry"
    expect(screen.getByText("retry")).toBeInTheDocument();
  });

  it("should render retry button with custom label", () => {
    render(
      <ListPageError
        message="Error"
        onRetry={jest.fn()}
        retryLabel="Try Again"
      />
    );

    expect(screen.getByText("Try Again")).toBeInTheDocument();
  });

  it("should call onRetry when retry button is clicked", async () => {
    const user = userEvent.setup();
    const handleRetry = jest.fn();

    render(<ListPageError message="Error" onRetry={handleRetry} />);

    await user.click(screen.getByText("retry"));

    expect(handleRetry).toHaveBeenCalledTimes(1);
  });
});

// ---- ListPageSkeleton ----

describe("ListPageSkeleton", () => {
  it("should render default 3 skeleton cards", () => {
    const { container } = render(<ListPageSkeleton />);

    const cards = container.querySelectorAll("[class*='bg-card']");
    expect(cards).toHaveLength(3);
  });

  it("should render custom number of skeleton cards", () => {
    const { container } = render(<ListPageSkeleton count={5} />);

    const cards = container.querySelectorAll("[class*='bg-card']");
    expect(cards).toHaveLength(5);
  });

  it("should render skeleton cards in a grid layout", () => {
    const { container } = render(<ListPageSkeleton />);

    const grid = container.firstChild;
    expect(grid).toHaveClass("grid");
  });

  it("should render single skeleton card when count is 1", () => {
    const { container } = render(<ListPageSkeleton count={1} />);

    const cards = container.querySelectorAll("[class*='bg-card']");
    expect(cards).toHaveLength(1);
  });
});
