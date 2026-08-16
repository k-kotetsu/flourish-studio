import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { PurposeProposal } from "../api/purposeProposals";
import { usePurposeProposalsStore } from "./purposeProposals";

const PROPOSALS: PurposeProposal[] = [
  { direction: "SELF", label: "自分の納得を軸に", statement: "自分で選んだと言えることを積み重ねて生きていきたい。" },
  { direction: "OTHERS", label: "まわりの人とともに", statement: "まわりの人が安心して力を出せる存在でありたい。" },
  { direction: "SOCIETY", label: "もっと広く", statement: "人の可能性が広がる場をつくっていきたい。" },
];

describe("usePurposeProposalsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("初期状態は空", () => {
    const store = usePurposeProposalsStore();

    expect(store.proposals).toEqual([]);
    expect(store.selectedDirection).toBeNull();
    expect(store.selectedProposal).toBeNull();
  });

  it("setProposalsで3案が記録され、選択はリセットされる", () => {
    const store = usePurposeProposalsStore();
    store.select("SELF");

    store.setProposals(PROPOSALS);

    expect(store.proposals).toEqual(PROPOSALS);
    expect(store.selectedDirection).toBeNull();
  });

  it("selectで選択した方向が記録され、selectedProposalがその案を返す", () => {
    const store = usePurposeProposalsStore();
    store.setProposals(PROPOSALS);

    store.select("OTHERS");

    expect(store.selectedDirection).toBe("OTHERS");
    expect(store.selectedProposal).toEqual(PROPOSALS[1]);
  });

  it("resetで空に戻る", () => {
    const store = usePurposeProposalsStore();
    store.setProposals(PROPOSALS);
    store.select("SELF");

    store.reset();

    expect(store.proposals).toEqual([]);
    expect(store.selectedDirection).toBeNull();
  });
});
