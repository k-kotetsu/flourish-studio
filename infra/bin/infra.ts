#!/usr/bin/env node
import * as cdk from "aws-cdk-lib/core";
import { DataStack } from "../lib/data-stack";
import { AuthStack } from "../lib/auth-stack";
import { AppStack } from "../lib/app-stack";
import { EdgeStack } from "../lib/edge-stack";

const app = new cdk.App();

const domainName = "dev.flourish-st.com";

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

const dataStack = new DataStack(app, "DataStack", { env });

const authStack = new AuthStack(app, "AuthStack", {
  env,
  domainName,
  cognitoDomainPrefix: "flourish-st-dev",
  // クライアントIDは機密情報ではない。シークレットはSecrets Managerから参照する。
  googleClientId:
    "834684313682-8ilfh4c2oar51mken8963etv7a731l14.apps.googleusercontent.com",
});

const appStack = new AppStack(app, "AppStack", {
  env,
  crossRegionReferences: true,
  table: dataStack.table,
  userPool: authStack.userPool,
  userPoolClient: authStack.userPoolClient,
});

// WAF(CLOUDFRONTスコープ)とACM証明書はus-east-1に置く(技術構成10.4)。
// AppStackはap-northeast-1のため、EdgeStackとはリージョンをまたぐ参照になる。
new EdgeStack(app, "EdgeStack", {
  env: { account: env.account, region: "us-east-1" },
  crossRegionReferences: true,
  domainName,
  // ACM証明書検索用のapexドメイン。P1-3でapex + *.flourish-st.comの証明書を作成済み。
  certificateDomainName: "flourish-st.com",
  hostedZoneId: "Z0416565YMZIN1UIDKI5",
  hostedZoneName: "flourish-st.com",
  api: appStack.api,
});
