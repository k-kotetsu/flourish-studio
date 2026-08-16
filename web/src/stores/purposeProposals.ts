import { defineStore } from "pinia";
import type { PurposeDirection, PurposeProposal } from "../api/purposeProposals";

/**
 * S-33が生成した3案と、S-34での選択をクライアント側に保持する。
 * S-32→S-33の`assessmentQuestions`/`assessmentResult`ストアと同じく、URLではなく
 * クライアント状態でS-35(P3-8、未実装)へ渡す想定。
 */
export const usePurposeProposalsStore = defineStore("purposeProposals", {
  state: () => ({
    proposals: [] as PurposeProposal[],
    selectedDirection: null as PurposeDirection | null,
  }),
  getters: {
    selectedProposal: (state): PurposeProposal | null =>
      state.proposals.find((proposal) => proposal.direction === state.selectedDirection) ?? null,
  },
  actions: {
    setProposals(proposals: PurposeProposal[]): void {
      this.proposals = proposals;
      this.selectedDirection = null;
    },
    select(direction: PurposeDirection): void {
      this.selectedDirection = direction;
    },
    reset(): void {
      this.proposals = [];
      this.selectedDirection = null;
    },
  },
});
