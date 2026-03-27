import { describe, expect, it, vi } from "vitest";

import { openAttachmentFilePicker } from "../attachmentUploadUtils";

describe("openAttachmentFilePicker", () => {
  it("falls back to click when showPicker throws", () => {
    const input = document.createElement("input");
    input.type = "file";

    const clickSpy = vi.spyOn(input, "click").mockImplementation(() => {});
    const showPickerSpy = vi
      .fn()
      .mockImplementation(() => {
        throw new DOMException("Not allowed", "NotAllowedError");
      });

    Object.assign(input, { showPicker: showPickerSpy });

    openAttachmentFilePicker(input);

    expect(showPickerSpy).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
  });
});
