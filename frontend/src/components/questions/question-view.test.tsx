import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Markdown } from "./markdown";
import { isComplete, QuestionView } from "./question-view";

const options = [
  { id: "a", text: "Newton" },
  { id: "b", text: "Joule" },
];

describe("isComplete", () => {
  it.each([
    ["mcq_single", {}, { selected: "a" }, true],
    ["mcq_single", {}, {}, false],
    ["mcq_multi", {}, { selected: [] }, false],
    ["mcq_multi", {}, { selected: ["a"] }, true],
    ["numerical", {}, { value: "  " }, false],
    ["numerical", {}, { value: "2.5" }, true],
    ["fill_blank", { blanks: 2 }, { values: ["x", ""] }, false],
    ["fill_blank", { blanks: 2 }, { values: ["x", "y"] }, true],
    [
      "match",
      {
        left: [
          { id: "l1", text: "" },
          { id: "l2", text: "" },
        ],
      },
      { pairs: { l1: "r1" } },
      false,
    ],
    ["subjective", {}, { text: "because" }, true],
  ] as const)("%s %j %j → %s", (type, content, response, expected) => {
    expect(isComplete(type, content, response)).toBe(expected);
  });
});

describe("QuestionView", () => {
  it("selects an option and reports the response", async () => {
    const onChange = vi.fn();
    render(
      <QuestionView type="mcq_single" stem="Unit of force?" content={{ options }} response={{}} onChange={onChange} />,
    );
    await userEvent.click(screen.getByText("Newton"));
    expect(onChange).toHaveBeenCalledWith({ selected: "a" });
  });

  it("locks inputs and marks right and wrong after answering", () => {
    render(
      <QuestionView
        type="mcq_single"
        stem="Unit of force?"
        content={{ options }}
        response={{ selected: "b" }}
        onChange={vi.fn()}
        reveal={{ correct: "a" }}
      />,
    );
    for (const r of screen.getAllByRole("radio")) expect(r).toBeDisabled();
    expect(screen.getByText("Newton").closest("label")).toHaveClass("border-success");
    expect(screen.getByText("Joule").closest("label")).toHaveClass("border-destructive");
  });

  it("shows the correct numerical answer with its unit once revealed", () => {
    render(
      <QuestionView
        type="numerical"
        stem="a?"
        content={{ unit: "m/s²" }}
        response={{ value: "3" }}
        reveal={{ value: 4, unit: "m/s²" }}
      />,
    );
    expect(screen.getByText(/Correct answer:/)).toHaveTextContent("Correct answer: 4 m/s²");
  });
});

describe("Markdown", () => {
  it("renders maths but never raw HTML from content", () => {
    const { container } = render(
      <Markdown>{"Force $F = ma$ <img src=x onerror=alert(1)> <script>alert(1)</script>"}</Markdown>,
    );
    expect(container.querySelector(".katex")).not.toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
  });
});
