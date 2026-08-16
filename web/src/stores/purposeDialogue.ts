import { defineStore } from "pinia";
import type { PurposeDialogueMessage } from "../api/purposeDialogue";

/**
 * S-32(AI対話)の対話履歴をクライアント側に保持する。対話履歴はサーバーに残さず、
 * リクエストのたびに全部送る(09_API設計3.2)。確定時(`POST /purposes`、P3-8)に
 * まとめて保存する想定で、それまではこのストアだけが対話全文を持つ。
 */
export const usePurposeDialogueStore = defineStore("purposeDialogue", {
  state: () => ({
    messages: [] as PurposeDialogueMessage[],
    remaining: 3,
  }),
  getters: {
    // 3往復完了後も対話は続けられる(wireframe-spec.md)。「候補を作る」の出現条件のみに使う
    canCreateProposals: (state) => state.remaining <= 0 && state.messages.length > 0,
  },
  actions: {
    addMessage(message: PurposeDialogueMessage): void {
      this.messages.push(message);
    },
    setRemaining(remaining: number): void {
      this.remaining = remaining;
    },
    reset(): void {
      this.messages = [];
      this.remaining = 3;
    },
  },
});
