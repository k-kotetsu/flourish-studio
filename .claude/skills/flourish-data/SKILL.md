---
name: flourish-data
description: Flourish Studio の DynamoDB アクセスを書くときの規則。単一テーブルのキー設計、集約を1アイテムにまとめる方針、バージョン管理、条件付き書き込み、TTL、トランザクションの型が入っている。「データを保存する」「リポジトリ層を書く」「テーブル設計」「クエリを書く」で発動する。
---

# DynamoDB アクセスの規則

## テーブル

| テーブル | 内容 | GSI |
|---|---|---|
| `flourish` | ユーザーデータのすべて | **なし** |
| `flourish_article` | 記事 | `category-index` |

**主テーブルにGSIを追加しない。** 全ての読み取りが PK 指定（または PK ＋ SK前方一致）で足りるように設計されている。GSIが要ると思ったら、まず設計を疑う。

## キーの一覧（これがすべて）

| 対象 | PK | SK | TTL |
|---|---|---|---|
| ユーザー本体 | `USER#<user_id>` | `PROFILE` | − |
| 現在地レポート | `USER#<id>` / `GUEST#<id>` | `ASSESSMENT#<assessment_id>` | ゲスト側のみ30日 |
| ありたい姿（現行） | `USER#<id>` | `PURPOSE#CURRENT` | − |
| 領域の計画（現行） | `USER#<id>` | `AREA#<AREA>#CURRENT` | − |
| 週次の振り返り | `USER#<id>` | `REFLECTION#<answered_at>#<id>` | − |
| 過去バージョン | `USER#<id>` | `HIST#...` | − |
| ゲストセッション | `GUEST#<guest_id>` | `GUEST` | 30日 |
| ログインセッション | `SESSION#<token_hash>` | `SESSION` | 30日 |
| 非同期ジョブ | `JOB#<job_id>` | `JOB` | 7日 |
| 冪等キー | `IDEM#<owner>#<key>` | `IDEM` | 24時間 |
| レート制限 | `RATE#<owner>#<window>` | `RATE` | 枠終了＋1時間 |

**`user_id` は Cognito の `sub` をそのまま使う。** 別IDを採番して対応表を持たない。

## 集約を1アイテムにまとめる

**関連する子要素を別アイテムにしない。親アイテムの中にリストとして持つ。**

| 集約 | 内包するもの |
|---|---|
| `ASSESSMENT` | 選択式24問 ＋ 自由記述8問 ＋ 問い文 ＋ 結果一式（約33KB） |
| `PURPOSE` | 選択式回答 ＋ 対話全文 ＋ 確定文 |
| `AREA_PLAN` | 選択式回答 ＋ 対話全文 ＋ 理想状態 ＋ **目標1〜3** |
| `REFLECTION` | 目標ごとの評価 ＋ 自由記述 ＋ AI出力 |

これにより「**成功した時点ではじめて保存される。失敗時は何も残らない**」（`09_API設計` 5.3）が、1回の `PutItem` で自明に満たされる。

上限400KBに対し最大でも33KB。**余裕がある。分割しない。**

## バージョン管理

現行は `#CURRENT`、過去は `HIST#` 接頭辞。

```
USER#a1b2  |  PURPOSE#CURRENT              ← version: 2
USER#a1b2  |  HIST#PURPOSE#000001
USER#a1b2  |  AREA#CAREER#CURRENT          ← version: 1
USER#a1b2  |  HIST#AREA#CAREER#000000      （なし）
```

**「現行版は1件」という一意制約は、キーの形が保証する。** `is_current` フラグを持たない。

`HIST#` に分けているのは、`begins_with('PURPOSE')` / `begins_with('AREA')` に過去版が混ざらないようにするため。

### 更新の型

```python
# 1. 現行版を読む
old = get_item(PK=f"USER#{uid}", SK="PURPOSE#CURRENT")
n = old["version"] if old else 0

# 2. 履歴退避と新版書き込みを1トランザクションで
transact_write_items([
    {"Put": {                       # 旧版がある場合のみ
        "Item": {**old, "SK": f"HIST#PURPOSE#{n:06d}"},
    }},
    {"Put": {
        "Item": {**new, "SK": "PURPOSE#CURRENT", "version": n + 1},
        "ConditionExpression": "attribute_not_exists(PK) OR version = :n",
        "ExpressionAttributeValues": {":n": n},
    }},
])
```

**条件式を必ず付ける。** 同時更新で片方が黙って消えることを防ぐ。

## 外部キーの代わりに ConditionCheck

「ありたい姿なしに領域は作れない」のような参照制約は、**トランザクション内の `ConditionCheck`** で守る。

```python
transact_write_items([
    {"ConditionCheck": {                       # 409 PURPOSE_REQUIRED
        "Key": {"PK": f"USER#{uid}", "SK": "PURPOSE#CURRENT"},
        "ConditionExpression": "attribute_exists(PK)",
    }},
    {"Put": {"Item": hist_item}},
    {"Put": {"Item": area_plan_item}},
])
```

## 冪等性・レート制限は条件付き書き込みで

**読んでから書かない。同時リクエストで壊れる。**

```python
# 冪等性：条件付き挿入の失敗が、そのまま判定になる
put_item(Item={"PK": f"IDEM#{owner}#{key}", ...},
         ConditionExpression="attribute_not_exists(PK)")
# → ConditionalCheckFailedException なら既存の job_id を返す

# レート制限：上限判定と加算を1回の書き込みで
update_item(Key={"PK": f"RATE#{owner}#{window}", "SK": "RATE"},
            UpdateExpression="ADD #c :one SET expires_at = :exp",
            ConditionExpression="attribute_not_exists(#c) OR #c < :limit")
```

## 読み取りの型

| 用途 | 呼び方 |
|---|---|
| `GET /home` | **`BatchGetItem`（6キー：PROFILE ＋ PURPOSE#CURRENT ＋ AREA#×4）** |
| `GET /reflections/context` | `BatchGetItem`（AREA#×4。目標はその中） |
| 振り返りの履歴 | `Query(PK, SK begins_with 'REFLECTION#', ScanIndexForward=False, Limit=N)` |
| 単体取得 | `GetItem` |

**`Scan` を書かない。** 必要になったら設計が間違っている。

## TTL

**TTLを設定してよいのは6種だけ**（上の表）。いずれも保持期間が明示的に決まっており、内面の記録ではない。

**ユーザーが所有する成果物にTTLを設定しない。** TTLは物理削除であり、「論理削除のみ」の方針（`08_データモデル` 11.1）に反する。退会は `PROFILE.deleted_at` に値を入れ、読み取り側で除外する。

ゲストの現在地レポートには、ゲストセッションと同じ `expires_at` を持たせる。**これが「未変換のレポートはゲストセッションと一緒に削除する」の実装。**

## 属性の扱い

| 変更 | 可否 |
|---|---|
| 属性の追加 | **可。** 読み取り側で欠損を許容する |
| 属性の意味の変更 | **不可。** 新しい属性名を足す |
| 属性の削除 | **不可** |
| キー設計の変更 | 移行スクリプト。デプロイと分離して手動実行 |

論理削除のみの方針の下では古いアイテムが残り続ける。**読み取り側は常に欠損と旧形式を許容する。**

## 制約はアプリが守る

DBが守ってくれない。**リポジトリ層を1箇所に集約し、検証を通らない書き込み経路を作らない。**

| 制約 | 値 |
|---|---|
| `scale_answers` | ちょうど24件、`(area, question_kind, item_code)` 重複なし、score 0〜4 |
| `free_text_answers` | ちょうど8件、`body` は null 可、`generated_question` 必須 |
| `result.areas` | ちょうど4件 |
| `goals` | 1〜3件 |
| `statuses` | 現行の全目標に1件ずつ |

**ユニットテストでこれらを必ず突く。**

## 出典

`docs/08_データモデル/logical-data-model.md`（アイテムの完全なJSON例あり）
選定理由は `docs/11_技術構成/adr-001-database-selection.md`
