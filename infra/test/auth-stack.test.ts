import * as cdk from "aws-cdk-lib/core";
import { Template } from "aws-cdk-lib/assertions";
import { AuthStack } from "../lib/auth-stack";

function synth(): Template {
  const app = new cdk.App();
  const stack = new AuthStack(app, "AuthStack", {
    env: { account: "123456789012", region: "ap-northeast-1" },
    stage: "dev",
    domainName: "dev.flourish-st.com",
    cognitoDomainPrefix: "flourish-st-dev",
    googleClientId: "dummy-client-id.apps.googleusercontent.com",
  });
  return Template.fromStack(stack);
}

describe("AuthStack", () => {
  it("パスワードポリシーが8文字以上・英字と数字を要求する", () => {
    const template = synth();
    template.hasResourceProperties("AWS::Cognito::UserPool", {
      Policies: {
        PasswordPolicy: {
          MinimumLength: 8,
          RequireLowercase: true,
          RequireNumbers: true,
          RequireSymbols: false,
          RequireUppercase: false,
        },
      },
      AutoVerifiedAttributes: [],
    });
  });

  it("メールのみをリカバリ手段にする", () => {
    const template = synth();
    template.hasResourceProperties("AWS::Cognito::UserPool", {
      AccountRecoverySetting: {
        RecoveryMechanisms: [{ Name: "verified_email", Priority: 1 }],
      },
    });
  });

  it("Cognito Hosted Domainが設定される", () => {
    const template = synth();
    template.hasResourceProperties("AWS::Cognito::UserPoolDomain", {
      Domain: "flourish-st-dev",
    });
  });

  it("App ClientはCookie/BFF方式に沿って認可コードグラントとシークレットを持つ", () => {
    const template = synth();
    template.hasResourceProperties("AWS::Cognito::UserPoolClient", {
      GenerateSecret: true,
      AllowedOAuthFlows: ["code"],
      CallbackURLs: ["https://dev.flourish-st.com/api/v1/auth/google/callback"],
    });
  });

  it("App ClientはログインのADMIN_USER_PASSWORD_AUTHフローを許可する(P3-2)", () => {
    const template = synth();
    template.hasResourceProperties("AWS::Cognito::UserPoolClient", {
      ExplicitAuthFlows: ["ALLOW_ADMIN_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
    });
  });

  it("Google連携用のシークレットを用意する(値は空でコードに含めない)", () => {
    const template = synth();
    template.hasResourceProperties("AWS::SecretsManager::Secret", {
      Name: "flourish/google-oauth-client-secret-dev",
    });
  });

  it("UserPoolは削除保護(RETAIN)される", () => {
    const template = synth();
    const pools = template.findResources("AWS::Cognito::UserPool");
    for (const resource of Object.values(pools)) {
      expect(resource.DeletionPolicy).toBe("Retain");
      expect(resource.UpdateReplacePolicy).toBe("Retain");
    }
  });
});
