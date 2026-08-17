import { defineStore } from "pinia";
import type { AreaDirection, AreaProposal } from "../api/areaProposals";

/**
 * S-53が生成した3案と、S-54での選択をクライアント側に保持する。
 * `purposeProposals`ストア(P3-7)と同じく、S-55(P4-5、未実装)へURLではなくクライアント状態で渡す想定。
 */
export const useAreaProposalsStore = defineStore("areaProposals", {
  state: () => ({
    proposals: [] as AreaProposal[],
    selectedDirection: null as AreaDirection | null,
  }),
  getters: {
    selectedProposal: (state): AreaProposal | null =>
      state.proposals.find((proposal) => proposal.direction === state.selectedDirection) ?? null,
  },
  actions: {
    setProposals(proposals: AreaProposal[]): void {
      this.proposals = proposals;
      this.selectedDirection = null;
    },
    select(direction: AreaDirection): void {
      this.selectedDirection = direction;
    },
    reset(): void {
      this.proposals = [];
      this.selectedDirection = null;
    },
  },
});
