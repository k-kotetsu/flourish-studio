#!/usr/bin/env node
import * as cdk from "aws-cdk-lib/core";
import { DataStack } from "../lib/data-stack";
import { AuthStack } from "../lib/auth-stack";
import { AppStack } from "../lib/app-stack";
import { EdgeStack } from "../lib/edge-stack";
import { Stage } from "../lib/stage";

const app = new cdk.App();

// `-c env=dev`/`-c env=prod`で切り替える。同一AWSアカウント内でdev/prodを分離するため、
// スタックID・物理名(テーブル名・キュー名など)の両方にこの値をsuffixとして使う(P7-10)。
const contextEnv = app.node.tryGetContext("env") as string | undefined;
const stage: Stage = contextEnv === "prod" ? "prod" : "dev";
if (contextEnv !== undefined && contextEnv !== "dev" && contextEnv !== "prod") {
  throw new Error(`unknown context "env": ${contextEnv} (expected "dev" or "prod")`);
}

// prodはP1-3で証明書を取得済みのapexドメイン、devはそのサブドメインを使う
// (`11_技術構成`10.4、ACM証明書はapex + `*.flourish-st.com`のワイルドカードでISSUED済み)。
const domainName = stage === "prod" ? "flourish-st.com" : "dev.flourish-st.com";
// Cognito Hosted Domainのプレフィックスは全AWSアカウント間でグローバルに一意である必要がある。
// 【判断】prod用の値はdocsに定義が無いため、既存の`flourish-st-dev`と対称になる
// `flourish-st-prod`を採用した(P7-10)。
const cognitoDomainPrefix = stage === "prod" ? "flourish-st-prod" : "flourish-st-dev";

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const dataStack = new DataStack(app, `DataStack-${stage}`, { env, stage });

const authStack = new AuthStack(app, `AuthStack-${stage}`, {
  env,
  stage,
  domainName,
  cognitoDomainPrefix,
  // クライアントIDは機密情報ではない。シークレットはSecrets Managerから参照する。
  // 【判断】dev/prodともに同じGoogle OAuthクライアントを使う想定。Googleは1クライアントに
  // 複数の承認済みリダイレクトURIを登録できるため、prod用コールバックURL
  // (`https://flourish-st.com/api/v1/auth/google/callback`)をGoogle Cloud Console側で
  // 追加登録する作業が人の手で必要(P7-10、別アカウントに分ける決定はしていない)。
  googleClientId:
    "834684313682-8ilfh4c2oar51mken8963etv7a731l14.apps.googleusercontent.com",
});

const appStack = new AppStack(app, `AppStack-${stage}`, {
  env,
  stage,
  crossRegionReferences: true,
  table: dataStack.table,
  userPool: authStack.userPool,
  userPoolClient: authStack.userPoolClient,
  domainName,
  cognitoDomainPrefix,
});

// WAF(CLOUDFRONTスコープ)とACM証明書はus-east-1に置く(技術構成10.4)。
// AppStackはap-northeast-1のため、EdgeStackとはリージョンをまたぐ参照になる。
new EdgeStack(app, `EdgeStack-${stage}`, {
  env: { account: env.account, region: "us-east-1" },
  crossRegionReferences: true,
  domainName,
  // ACM証明書検索用のapexドメイン。P1-3でapex + *.flourish-st.comの証明書を作成済み。
  // dev/prod共通の1枚の証明書(ワイルドカード)でどちらのdomainNameも検証できる。
  certificateDomainName: "flourish-st.com",
  hostedZoneId: "Z0416565YMZIN1UIDKI5",
  hostedZoneName: "flourish-st.com",
  api: appStack.api,
});
