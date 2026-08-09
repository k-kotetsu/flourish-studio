---
name: flourish-api
description: Flourish Studio のAPIエンドポイントを追加・変更するときの規則。認証Cookie、エラー応答の形、ステータスコード、冪等性、レート制限、非同期ジョブ、SSEストリーミングの型が入っている。「エンドポイントを実装する」「認証を追加する」「ジョブを作る」「エラーを返す」で発動する。
---

# API実装の規則

ベースパス `/api/v1`。**REST。同一ドメイン構成のため CORS 設定は不要。**

## 入力途中を送らない

**S-12・S-14・S-31〜S-34・S-51〜S-55 の入力はクライアントが保持する。** サーバは下書きを持たない。AI対話の履歴も同じで、リクエストのたびに必要な文脈をすべて送る。

結果として**AI関連のエンドポイントはステートレス**になる。確定時のエンドポイントだけが書き込みを行う。

**「途中保存API」を足さない。** 足したくなったら仕様の読み違い。

## 認証

| Cookie | 発行 | 属性 |
|---|---|---|
| `fs_guest` | S-11 到達時 | `HttpOnly` `Secure` `SameSite=Lax` `Max-Age=2592000` |
| `fs_session` | ログイン・登録成功時 | 同上 |

- 値は**不透明なランダム文字列（128ビット以上）**。中にIDを埋めない。サーバ側で引く
- **Cognitoのトークンをブラウザに渡さない**（BFF方式）。`SESSION` アイテムを引いて `user_id` を得る
- `SESSION#` の PK にはトークンではなく**ハッシュ**を入れる
- 有効期限の延長は**前回から24時間以上経っている場合のみ**（毎リクエスト書き込まない）

| 認証レベル | 対象 |
|---|---|
| 不要 | 記事、トップページ |
| ゲスト可 | 現在地レポート関連 |
| 要ログイン | ありたい姿以降のすべて |

未認証なら `401`。クライアントは S-01 へ戻す。

## ステータスコード

| コード | 用途 |
|---|---|
| `200` / `201` / `204` | 取得・更新 / 作成 / 削除・ログアウト |
| **`202`** | **非同期ジョブを受け付けた** |
| `400` | リクエストの形式が不正 |
| `401` / `403` / `404` | 未認証 / 他人のリソース / 存在しない |
| `409` | 状態が合わない（例：目標0件で振り返り開始） |
| `422` | 形式は正しいが業務ルールに反する（例：選択式が24件揃っていない） |
| `429` | レート制限。`Retry-After` を返す |
| `503` | AIプロバイダ側の障害 |

## エラー応答

```json
{
  "error": {
    "code": "ANSWERS_INCOMPLETE",
    "message": "scale answers must be exactly 24 (received 23)",
    "details": [{ "field": "scale_answers", "reason": "missing area=SOCIAL kind=COMMITMENT" }]
  }
}
```

| フィールド | 用途 |
|---|---|
| `code` | **クライアントが分岐に使う。** 追加はしても意味は変えない |
| `message` | **開発者向け。英語。ユーザーには表示しない** |
| `details` | 任意 |

**サーバはユーザー向け文面を持たない。** クライアントが `code` から文面を決める。文面のトーンは `flourish-tone` 参照。

## 冪等性

生成系の `POST` は `Idempotency-Key` ヘッダを受け付ける。**同じキーの再送には新しいジョブを作らず、既存の `job_id` を返す。**

「もう一度やってみる」ボタンは新しいキーを送るので、意図した再試行は通る。

実装は条件付き挿入（`flourish-data` 参照）。

## レート制限

| 対象 | 制限 |
|---|---|
| ゲスト（`fs_guest`） | レポート生成 **1セッション3回**（初回＋再試行2回） |
| 登録済み | 生成系すべてで **1時間30回** |

超過時は `429` ＋ `Retry-After`。**WAFではなくアプリ層で実装する**（ユーザー単位の業務ルールのため）。

## AI生成の3方式

**判断の基準は、独立した生成中画面を挟むかどうか。**

| 方式 | 使う場面 | 対象画面 |
|---|---|---|
| **非同期ジョブ** | 画面遷移を伴う長い生成 | S-13 / S-15 / S-33 / S-53 / S-62 |
| **ストリーミング（SSE）** | チャットの応答 | S-32 / S-52 |
| **同期** | 画面内で待つ短い生成 | S-56 のAIヒント（**10秒でタイムアウト**） |

### 非同期ジョブ

```
POST /assessments  →  202 { job_id, poll_after_ms: 1500 }
GET  /jobs/{id}    →  200 { status: "RUNNING" }
                   →  200 { status: "SUCCEEDED", result: {...} }
                   →  200 { status: "FAILED", error: { code, retryable } }
```

- 状態は `QUEUED` / `RUNNING` / `SUCCEEDED` / `FAILED`
- **ポーリング間隔はサーバが `poll_after_ms` で指示する。** クライアントは固定値を持たない
- **サーバは自動で再試行しない。** `FAILED` を返し、ユーザーが押したら新しいジョブを作る
  - SQS も `maxReceiveCount = 1`。再送させると1回の操作で複数回AI課金が発生する
- `retryable` はクライアントが再試行ボタンを出すかの判断に使う
- **ジョブは発行元のセッションからのみ参照できる。** 他人のIDなら `403`
- 成果物とジョブ完了を**同一トランザクション**で書く

### ストリーミング（SSE）

```
event: delta  { "text": "「成長」を" }
event: done   { "turn": 1, "remaining": 2, "safety_flag": false }
event: error
```

- **対話履歴はサーバに残さない。** クライアントが保持し、次のリクエストで全部送る。確定時（`POST /purposes`）にまとめて保存
- **`turn` と `remaining` はコードが数える。** AIに数えさせない
- API Gateway のメソッドに `ResponseTransferMode: STREAM` が要る
- CloudFront の該当ビヘイビアは**圧縮を無効にする**（バッファされてSSEが壊れる）

## エンドポイント一覧

```
POST /guest-sessions              不要      S-11
POST /ai/assessment-questions     ゲスト可  S-13   → 202
POST /assessments                 ゲスト可  S-15   → 202
GET  /assessments/{id}            ゲスト可  S-16
POST /auth/register               不要      S-21
POST /auth/login                  不要      S-02
GET  /auth/google                 不要      S-21 / S-02
GET  /auth/google/callback        不要      −
POST /auth/logout                 要ログイン −
GET  /me                          要ログイン 全体
PATCH /me                         要ログイン S-41（テーマ切替）
POST /ai/purpose-dialogue         要ログイン S-32   → SSE
POST /ai/purpose-proposals        要ログイン S-33   → 202
POST /purposes                    要ログイン S-35
GET  /purposes/current            要ログイン S-36
PUT  /purposes/current            要ログイン S-37
GET  /home                        要ログイン S-41
POST /ai/area-dialogue            要ログイン S-52   → SSE
POST /ai/area-proposals           要ログイン S-53   → 202
POST /ai/goal-hints               要ログイン S-56   → 同期
POST /area-plans                  要ログイン S-56
GET  /area-plans/{area}           要ログイン S-57
PUT  /area-plans/{area}           要ログイン S-58
GET  /reflections/context         要ログイン S-61
POST /reflections                 要ログイン S-62   → 202
GET  /reflections/{id}            要ログイン S-63
GET  /jobs/{id}                   発行者のみ 生成中画面すべて
```

**記事（K-01 / K-02）はAPIを持たない。** ビルド時に静的HTMLを生成する。

**`/home` は画面専用エンドポイント。** RESTの原則から外れるが、ホームで4〜5回往復させないために置く。**画面専用エンドポイントはここだけに留める。**

## 主な検証

| エンドポイント | 検証 | 失敗時 |
|---|---|---|
| `/ai/assessment-questions` `/assessments` | `scale_answers` ちょうど24件 | `422 ANSWERS_INCOMPLETE` |
| `/assessments` | `free_text_answers` ちょうど8件、`generated_question` 必須 | `422` |
| `/purposes` `/purposes/current` | `statement` 60文字以内、空不可 | `422 STATEMENT_TOO_LONG` |
| `/ai/purpose-proposals` `/ai/area-proposals` | **必ず3件、`direction` 重複なし** | 3件未満ならジョブを `FAILED`。**2案だけ見せない** |
| `/area-plans` | 目標 1〜3件 | `422 GOALS_REQUIRED` |
| `/area-plans` | 現行 `PURPOSE` の存在 | `409 PURPOSE_REQUIRED` |
| `/reflections` | 現行の全目標に1件ずつ | `422` |

## バージョンを上げる更新

`PUT /purposes/current` と `PUT /area-plans/{area}` は**上書きではなく新しいバージョンを作る**（`flourish-data` 参照）。

- `PUT /purposes/current` の `original_statement` には**前の版の文言**を入れる（AI原文ではない）
- **ありたい姿を変えても既存の `AREA_PLAN` は再作成しない**
- `PUT /area-plans/{area}` で `goal_key` を送らない目標は新規としてサーバが採番。送られなかった `goal_key` はその版で削除

## 出典

`docs/09_API設計/api-design.md`（リクエスト／レスポンスの完全なJSON例あり）
