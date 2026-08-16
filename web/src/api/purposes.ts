/**
 * `POST /purposes` ／ `GET`/`PUT /purposes/current`。09_API設計5.8・5.8.1、S-35/S-36/S-37。
 * `POST`は選択式回答・対話全文・選ばれた案・確定文を送り、ここではじめてありたい姿を保存する。
 * `GET`/`PUT`は保存済みのありたい姿を閲覧・編集する(`PUT`は上書きではなく新しいversionを作る)。
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

export interface PurposeResponse {
  version: number;
  statement: string;
  selected_direction: PurposeDirection;
  selected_label: string;
  created_at: string;
}

export function createPurpose(request: CreatePurposeRequest): Promise<PurposeResponse> {
  return api.post<PurposeResponse>("/purposes", request);
}

export function getCurrentPurpose(): Promise<PurposeResponse> {
  return api.get<PurposeResponse>("/purposes/current");
}

export function updateCurrentPurpose(statement: string): Promise<PurposeResponse> {
  return api.put<PurposeResponse>("/purposes/current", { statement });
}
