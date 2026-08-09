#!/usr/bin/env node
import * as cdk from "aws-cdk-lib/core";
import { DataStack } from "../lib/data-stack";

// AuthStack, AppStack, EdgeStack はP1-5〜P1-7で追加する。
// 参照: docs/11_技術構成/tech-architecture.md 10.1
const app = new cdk.App();

new DataStack(app, "DataStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
