import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { TutorMessage, TutorStatus } from "@/types/tutor";
import { Composer, linkCitations, MessageBubble, ModePicker, StatusNote } from "./chat";

const wrap = (ui: React.ReactElement) =>
  render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);

const reply = (over: Partial<TutorMessage> = {}): TutorMessage => ({
  id: "m1",
  role: "tutor",
  mode: "hint",
  content: "Which law links $F$ and $a$? [S1]",
  source: "ai",
  citations: [
    {
      id: "S1",
      chunk_id: 1,
      document_id: "d1",
      title: "Laws of Motion — study notes",
      heading: "Newton's second law (F = ma)",
      page: 3,
      excerpt: "The rate of change of momentum equals the net external force.",
    },
  ],
  flags: ["answer_withheld", "counts_as_hint"],
  actions: [{ type: "practice", concept_id: 7, label: "Practise Newton's second law" }],
  helpful: null,
  created_at: "2026-11-04T10:00:00Z",
  ...over,
});

describe("MessageBubble", () => {
  it("labels an AI reply, explains guardrails and lists its sources", async () => {
    const onAction = vi.fn();
    wrap(<MessageBubble m={reply()} onAction={onAction} />);
    expect(screen.getByText("AI tutor")).toBeInTheDocument();
    expect(screen.getByText(/held back so you can try it first/)).toBeInTheDocument();
    expect(screen.getByText(/counts like a hint/)).toBeInTheDocument();
    expect(screen.getByText("Newton's second law (F = ma)")).toBeInTheDocument();
    expect(screen.getByText(/p\. 3/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Practise Newton's second law/ }));
    expect(onAction).toHaveBeenCalledWith(expect.objectContaining({ concept_id: 7 }));
  });

  it("says when a reply came from study notes, and shows support replies without ratings", () => {
    const { unmount } = wrap(<MessageBubble m={reply({ source: "notes", flags: [] })} />);
    expect(screen.getByText("From your study notes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Helpful" })).toBeInTheDocument();
    unmount();
    wrap(<MessageBubble m={reply({ source: "safety", citations: [], actions: [], flags: [] })} />);
    expect(screen.getByText("Support")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Helpful" })).not.toBeInTheDocument();
  });

  it("shows a student's message as plain text", () => {
    wrap(<MessageBubble m={reply({ role: "student", content: "**not bold**" })} />);
    expect(screen.getByText("**not bold**")).toBeInTheDocument();
  });
});

describe("Composer", () => {
  it("sends on Enter, keeps Shift+Enter for new lines, and ignores blanks", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} pending={false} placeholder="Ask" />);
    const box = screen.getByLabelText("Message the tutor");
    await userEvent.type(box, "   {Enter}");
    expect(onSend).not.toHaveBeenCalled();
    await userEvent.type(box, "line one{Shift>}{Enter}{/Shift}line two{Enter}");
    expect(onSend).toHaveBeenCalledWith("line one\nline two");
    expect(box).toHaveValue("");
  });
});

describe("ModePicker", () => {
  it("is a radio group of the five modes", async () => {
    const onChange = vi.fn();
    render(<ModePicker value="teach" onChange={onChange} />);
    const radios = screen.getAllByRole("radio");
    expect(radios.map((r) => r.textContent)).toEqual([
      expect.stringContaining("Teach me"),
      expect.stringContaining("Give a hint"),
      expect.stringContaining("Solve with me"),
      expect.stringContaining("Test me"),
      expect.stringContaining("Find my mistake"),
    ]);
    expect(radios[0]).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("radio", { name: /Find my mistake/ }));
    expect(onChange).toHaveBeenCalledWith("mistake");
  });
});

describe("StatusNote", () => {
  const base: TutorStatus = {
    ai_available: false,
    reason: "not_configured",
    notice: "x",
    messages_today: 0,
    daily_limit: 40,
    modes: [],
  };
  it("explains notes mode when AI isn't available", () => {
    render(<StatusNote status={base} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/isn't switched on yet.*approved study notes/);
  });
  it("shows today's usage when AI is on", () => {
    render(<StatusNote status={{ ...base, ai_available: true, reason: null, messages_today: 3 }} />);
    expect(screen.getByText(/3 of 40 AI messages used today/)).toBeInTheDocument();
  });
});

describe("linkCitations", () => {
  it("links only citations to sources that exist", () => {
    const out = linkCitations("Use F = ma [S1]. See also [S1, S9] and [S7].", "m", new Set(["S1"]));
    expect(out).toBe("Use F = ma [S1](#m-S1). See also [S1](#m-S1) and [S7].");
  });
});
