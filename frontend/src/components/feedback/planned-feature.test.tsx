import { render, screen } from "@testing-library/react";
import { Target } from "lucide-react";
import { describe, expect, it } from "vitest";
import { studentPlanned } from "@/features/planned/catalog";
import { PlannedFeature } from "./planned-feature";

describe("PlannedFeature", () => {
  it("clearly labels unbuilt modules and states that nothing is simulated", () => {
    render(
      <PlannedFeature icon={Target} title="Practice" phase="Phase 1" description="d" capabilities={["One", "Two"]} />,
    );
    expect(screen.getByText(/Planned · Phase 1/)).toBeInTheDocument();
    expect(screen.getByText(/nothing on this page is simulated/i)).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("has an entry for every planned student nav item", async () => {
    const { studentNav } = await import("@/components/layout/nav");
    for (const item of studentNav.filter((i) => i.planned)) {
      expect(studentPlanned[item.href.slice(1)], item.href).toBeDefined();
    }
  });
});
