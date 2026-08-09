#!/usr/bin/env node
import * as cdk from "aws-cdk-lib/core";

// スタック（DataStack, AuthStack, AppStack, EdgeStack）はP1-4〜P1-7で追加する。
// 参照: docs/11_技術構成/tech-architecture.md 10.1
new cdk.App();
