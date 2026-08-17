import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useAreaDialogueStore } from "./areaDialogue";

describe("useAreaDialogueStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("初期状態は履歴が空でremainingは2", () => {
    const store = useAreaDialogueStore();

    expect(store.messages).toEqual([]);
    expect(store.remaining).toBe(2);
    expect(store.canCreateIdealState).toBe(false);
  });

  it("addMessageで履歴に追記される", () => {
    const store = useAreaDialogueStore();

    store.addMessage({ role: "AI", body: "起点の問い" });
    store.addMessage({ role: "USER", body: "回答" });

    expect(store.messages).toEqual([
      { role: "AI", body: "起点の問い" },
      { role: "USER", body: "回答" },
    ]);
  });

  it("remainingが0以下かつ履歴がある場合のみcanCreateIdealStateがtrueになる", () => {
    const store = useAreaDialogueStore();

    expect(store.canCreateIdealState).toBe(false);

    store.addMessage({ role: "AI", body: "問い" });
    store.setRemaining(0);

    expect(store.canCreateIdealState).toBe(true);
  });

  it("resetで初期状態に戻る", () => {
    const store = useAreaDialogueStore();
    store.addMessage({ role: "AI", body: "問い" });
    store.setRemaining(0);

    store.reset();

    expect(store.messages).toEqual([]);
    expect(store.remaining).toBe(2);
    expect(store.canCreateIdealState).toBe(false);
  });
});
