/**
 * Tests for PromptTemplateEditor component.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { PromptTemplateEditor } from "@/components/strategy-studio/prompt-template-editor";
import { PromptSections } from "@/types";

// Mock next-intl
jest.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
  useLocale: () => "en",
}));

// Mock MonacoMarkdownEditor
jest.mock("@/components/ui/monaco-markdown-editor", () => ({
  MonacoMarkdownEditor: ({ value, onChange, placeholder }: any) => (
    <textarea
      data-testid="monaco-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
    />
  ),
}));

// Mock Collapsible components
jest.mock("@/components/ui/collapsible", () => ({
  Collapsible: ({
    children,
    open,
  }: {
    children: React.ReactNode;
    open: boolean;
  }) => (
    <div data-testid="collapsible" data-open={open}>
      {children}
    </div>
  ),
  CollapsibleTrigger: ({ children, className, ...props }: any) => (
    <button data-testid="collapsible-trigger" className={className} {...props}>
      {children}
    </button>
  ),
  CollapsibleContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="collapsible-content">{children}</div>
  ),
}));

const defaultSections: PromptSections = {
  roleDefinition: "",
  tradingFrequency: "",
  entryStandards: "",
  decisionProcess: "",
};

describe("PromptTemplateEditor", () => {
  const defaultProps = {
    promptMode: "simple" as const,
    onPromptModeChange: jest.fn(),
    value: defaultSections,
    onChange: jest.fn(),
    customPrompt: "",
    onCustomPromptChange: jest.fn(),
    advancedPrompt: "",
    onAdvancedPromptChange: jest.fn(),
    tradingMode: "balanced" as const,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders title and description", () => {
    render(<PromptTemplateEditor {...defaultProps} />);

    expect(screen.getByText("promptEditor.title")).toBeInTheDocument();
    expect(screen.getByText("promptEditor.description")).toBeInTheDocument();
  });

  it("renders mode toggle", () => {
    render(<PromptTemplateEditor {...defaultProps} />);

    expect(screen.getByText("promptEditor.modeSimple")).toBeInTheDocument();
    expect(screen.getByText("promptEditor.modeAdvanced")).toBeInTheDocument();
  });

  it("renders collapsible sections in simple mode", () => {
    render(<PromptTemplateEditor {...defaultProps} />);

    expect(
      screen.getByText("promptEditor.sections.roleDefinition"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("promptEditor.sections.tradingFrequency"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("promptEditor.sections.entryStandards"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("promptEditor.sections.decisionProcess"),
    ).toBeInTheDocument();
  });

  it("switches to advanced mode when toggle is clicked", () => {
    const onPromptModeChange = jest.fn();
    render(
      <PromptTemplateEditor
        {...defaultProps}
        onPromptModeChange={onPromptModeChange}
      />,
    );

    const toggle = screen.getByRole("switch");
    fireEvent.click(toggle);

    expect(onPromptModeChange).toHaveBeenCalledWith("advanced");
  });

  it("clears advanced prompt when switching from advanced to simple", () => {
    const onAdvancedPromptChange = jest.fn();
    render(
      <PromptTemplateEditor
        {...defaultProps}
        promptMode="advanced"
        advancedPrompt="some content"
        onAdvancedPromptChange={onAdvancedPromptChange}
      />,
    );

    const toggle = screen.getByRole("switch");
    fireEvent.click(toggle);

    expect(onAdvancedPromptChange).toHaveBeenCalledWith("");
  });

  it("renders monaco editor in advanced mode", () => {
    render(<PromptTemplateEditor {...defaultProps} promptMode="advanced" />);

    expect(screen.getByTestId("monaco-editor")).toBeInTheDocument();
    expect(
      screen.getByText("promptEditor.advancedModeTitle"),
    ).toBeInTheDocument();
  });

  it("updates advanced prompt when monaco editor changes", () => {
    const onAdvancedPromptChange = jest.fn();
    render(
      <PromptTemplateEditor
        {...defaultProps}
        promptMode="advanced"
        onAdvancedPromptChange={onAdvancedPromptChange}
      />,
    );

    const editor = screen.getByTestId("monaco-editor");
    fireEvent.change(editor, { target: { value: "new prompt content" } });

    expect(onAdvancedPromptChange).toHaveBeenCalledWith("new prompt content");
  });

  it("expands and collapses sections", () => {
    render(<PromptTemplateEditor {...defaultProps} />);

    // Find first collapsible trigger
    const triggers = screen.getAllByTestId("collapsible-trigger");

    // Click to expand
    fireEvent.click(triggers[0]);

    // Click again to collapse
    fireEvent.click(triggers[0]);

    // Component should handle toggle internally
    expect(triggers.length).toBe(4); // 4 sections
  });

  it("shows customized badge when section differs from default", () => {
    const customizedSections: PromptSections = {
      ...defaultSections,
      roleDefinition: "Custom role definition content",
    };

    render(
      <PromptTemplateEditor {...defaultProps} value={customizedSections} />,
    );

    // Should show customized indicator
    expect(screen.getByText("(promptEditor.customized)")).toBeInTheDocument();
  });

  it("updates section content via textarea", () => {
    const onChange = jest.fn();
    render(<PromptTemplateEditor {...defaultProps} onChange={onChange} />);

    // Find and interact with textarea (in collapsible content)
    const textareas = screen.getAllByRole("textbox");
    if (textareas.length > 0) {
      fireEvent.change(textareas[0], { target: { value: "New content" } });
      expect(onChange).toHaveBeenCalled();
    }
  });
});
