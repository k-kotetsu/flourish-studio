import { defineStore } from "pinia";
import type { AreaDirection, AreaProposal } from "../api/areaProposals";

/**
 * S-53が生成した3案、S-54での選択、S-55(P4-5)での編集後の理想状態をクライアント側に保持する。
 * `purposeProposals`ストア(P3-7)と同じく、URLではなくクライアント状態で画面をまたいで渡す。
 * `editedIdealState`はS-56(P4-6、未実装)の`POST /area-plans`が`ideal_state`として使う想定
 * (選択直後の`selectedProposal.ideal_state`は`original_ideal_state`として別途参照する)。
 */
export const useAreaProposalsStore = defineStore("areaProposals", {
  state: () => ({
    proposals: [] as AreaProposal[],
    selectedDirection: null as AreaDirection | null,
    editedIdealState: null as string | null,
  }),
  getters: {
    selectedProposal: (state): AreaProposal | null =>
      state.proposals.find((proposal) => proposal.direction === state.selectedDirection) ?? null,
  },
  actions: {
    setProposals(proposals: AreaProposal[]): void {
      this.proposals = proposals;
      this.selectedDirection = null;
      this.editedIdealState = null;
    },
    select(direction: AreaDirection): void {
      this.selectedDirection = direction;
      // 選び直した案ごとに編集をやり直す(前の案の編集内容を持ち越さない)
      this.editedIdealState = null;
    },
    setEditedIdealState(value: string): void {
      this.editedIdealState = value;
    },
    reset(): void {
      this.proposals = [];
      this.selectedDirection = null;
      this.editedIdealState = null;
    },
  },
});
