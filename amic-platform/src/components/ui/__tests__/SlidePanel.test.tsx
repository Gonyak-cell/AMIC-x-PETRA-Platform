import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SlidePanel } from "../SlidePanel";

describe("SlidePanel", () => {
  it("allows file drags within the panel overlay", () => {
    const { container } = render(
      <SlidePanel open onClose={vi.fn()} title="Buyer Detail">
        <div>content</div>
      </SlidePanel>,
    );

    const dialog = container.querySelector("dialog");
    expect(dialog).not.toBeNull();

    const file = new File(["pdf"], "tm.pdf", { type: "application/pdf" });
    const dataTransfer = {
      files: [file],
      types: ["Files"],
      dropEffect: "none",
    };

    expect(
      fireEvent.dragOver(dialog as HTMLElement, {
        dataTransfer,
      }),
    ).toBe(false);
    expect(dataTransfer.dropEffect).toBe("copy");

    expect(
      fireEvent.dragOver(document.body, {
        dataTransfer,
      }),
    ).toBe(false);
  });
});
