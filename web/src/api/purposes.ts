/**
 * `POST /purposes`。09_API設計5.8、S-35。
 * 選択式回答・対話全文・選ばれた案・確定文を送り、ここではじめてありたい姿を保存する。
 */
import { api } from "./client";
import type { PurposeDialogueChoice, PurposeDialogueMessage } from "./purposeDialogue";
import type { PurposeDirection } from "./purposeProposals";

export interface CreatePurposeRequest {
  choices: PurposeDialogueChoice[];
  messages: PurposeDialogueMessage[];
  selected_direction: PurposeDirection;
  selected_label: string;
  original_statement: string;
  statement: string;
}

export interface CreatePurposeResponse {
  version: number;
  statement: string;
  selected_direction: PurposeDirection;
  selected_label: string;
  created_at: string;
}

export function createPurpose(request: CreatePurposeRequest): Promise<CreatePurposeResponse> {
  return api.post<CreatePurposeResponse>("/purposes", request);
}
