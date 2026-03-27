import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Modal } from "../Modal";

describe("Modal", () => {
  it("allows file drags within the dialog overlay", () => {
    const { container } = render(
      <Modal open onClose={vi.fn()} title="Upload">
        <div>content</div>
      </Modal>,
    );

    const dialog = container.querySelector("dialog");
    expect(dialog).not.toBeNull();

    const file = new File(["pdf"], "nda.pdf", { type: "application/pdf" });
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

    expect(
      fireEvent.dragOver(window, {
        dataTransfer,
      }),
    ).toBe(false);
  });
});
