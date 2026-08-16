import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { usePurposeDialogueStore } from "./purposeDialogue";

describe("usePurposeDialogueStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("初期状態は履歴が空でremainingは3", () => {
    const store = usePurposeDialogueStore();

    expect(store.messages).toEqual([]);
    expect(store.remaining).toBe(3);
    expect(store.canCreateProposals).toBe(false);
  });

  it("addMessageで履歴に追記される", () => {
    const store = usePurposeDialogueStore();

    store.addMessage({ role: "AI", body: "起点の問い" });
    store.addMessage({ role: "USER", body: "回答" });

    expect(store.messages).toEqual([
      { role: "AI", body: "起点の問い" },
      { role: "USER", body: "回答" },
    ]);
  });

  it("remainingが0以下かつ履歴がある場合のみcanCreateProposalsがtrueになる", () => {
    const store = usePurposeDialogueStore();

    expect(store.canCreateProposals).toBe(false);

    store.addMessage({ role: "AI", body: "問い" });
    store.setRemaining(0);

    expect(store.canCreateProposals).toBe(true);
  });

  it("resetで初期状態に戻る", () => {
    const store = usePurposeDialogueStore();
    store.addMessage({ role: "AI", body: "問い" });
    store.setRemaining(0);

    store.reset();

    expect(store.messages).toEqual([]);
    expect(store.remaining).toBe(3);
    expect(store.canCreateProposals).toBe(false);
  });
});
