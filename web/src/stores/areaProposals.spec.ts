import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { AreaProposal } from "../api/areaProposals";
import { useAreaProposalsStore } from "./areaProposals";

const PROPOSALS: AreaProposal[] = [
  { direction: "DEEPEN", label: "今の場所で深める", ideal_state: "自分の強みが言葉になっている。" },
  { direction: "CHANGE", label: "やり方を変える", ideal_state: "自分に合う進め方が見つかっている。" },
  { direction: "EXPAND", label: "外に出る", ideal_state: "会社の外でも通用する選択肢を持てている。" },
];

describe("useAreaProposalsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("初期状態は空", () => {
    const store = useAreaProposalsStore();

    expect(store.proposals).toEqual([]);
    expect(store.selectedDirection).toBeNull();
    expect(store.selectedProposal).toBeNull();
    expect(store.editedIdealState).toBeNull();
  });

  it("setProposalsで3案が記録され、選択と編集内容はリセットされる", () => {
    const store = useAreaProposalsStore();
    store.select("DEEPEN");
    store.setEditedIdealState("編集中の文");

    store.setProposals(PROPOSALS);

    expect(store.proposals).toEqual(PROPOSALS);
    expect(store.selectedDirection).toBeNull();
    expect(store.editedIdealState).toBeNull();
  });

  it("selectで選択した方向が記録され、selectedProposalがその案を返す", () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS);

    store.select("CHANGE");

    expect(store.selectedDirection).toBe("CHANGE");
    expect(store.selectedProposal).toEqual(PROPOSALS[1]);
  });

  it("selectし直すと、それまでの編集内容はリセットされる", () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS);
    store.select("DEEPEN");
    store.setEditedIdealState("編集中の文");

    store.select("CHANGE");

    expect(store.editedIdealState).toBeNull();
  });

  it("setEditedIdealStateで編集後の文を記録する", () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS);
    store.select("DEEPEN");

    store.setEditedIdealState("書き換えた理想の状態。");

    expect(store.editedIdealState).toBe("書き換えた理想の状態。");
  });

  it("resetで空に戻る", () => {
    const store = useAreaProposalsStore();
    store.setProposals(PROPOSALS);
    store.select("DEEPEN");
    store.setEditedIdealState("編集中の文");

    store.reset();

    expect(store.proposals).toEqual([]);
    expect(store.selectedDirection).toBeNull();
    expect(store.editedIdealState).toBeNull();
  });
});
