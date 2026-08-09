#!/usr/bin/env node
import * as cdk from "aws-cdk-lib/core";
import { DataStack } from "../lib/data-stack";
import { AuthStack } from "../lib/auth-stack";
import { AppStack } from "../lib/app-stack";

// EdgeStack はP1-7で追加する。
// 参照: docs/11_技術構成/tech-architecture.md 10.1
const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

new DataStack(app, "DataStack", { env });

new AuthStack(app, "AuthStack", {
  env,
  domainName: "dev.flourish-st.com",
  cognitoDomainPrefix: "flourish-st-dev",
  // クライアントIDは機密情報ではない。シークレットはSecrets Managerから参照する。
  googleClientId:
    "834684313682-8ilfh4c2oar51mken8963etv7a731l14.apps.googleusercontent.com",
});

new AppStack(app, "AppStack", { env });
