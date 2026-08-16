import * as cdk from "aws-cdk-lib/core";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";

export interface AuthStackProps extends cdk.StackProps {
  /** バックエンドがGoogle連携のコールバックを受けるドメイン（例: dev.flourish-st.com） */
  readonly domainName: string;
  /** Cognito Hosted Domainのプレフィックス。全AWS間でグローバルに一意である必要がある */
  readonly cognitoDomainPrefix: string;
  /** Google CloudのOAuthクライアントID（機密ではないためコードで持つ） */
  readonly googleClientId: string;
}

export class AuthStack extends cdk.Stack {
  readonly userPool: cognito.UserPool;
  readonly userPoolClient: cognito.UserPoolClient;
  readonly googleOAuthClientSecret: secretsmanager.Secret;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    // パスワード要件（技術構成7.4）：8文字以上、英字と数字を各1文字以上。
    // 「よく使われるパスワードの拒否」はCognitoにない機能のためバックエンド側で実装する。
    this.userPool = new cognito.UserPool(this, "UserPool", {
      userPoolName: "flourish-users",
      selfSignUpEnabled: true,
      signInAliases: { email: true },
      // AdminConfirmSignUpで確認するため、Cognito標準の確認コードメールは送らせない（技術構成7.2）。
      autoVerify: {},
      standardAttributes: {
        email: { required: true, mutable: true },
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: false,
        requireDigits: true,
        requireSymbols: false,
      },
      // 電話番号を収集しないため、CDKの既定値（電話番号優先）ではなくメールのみにする。
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    this.userPool.addDomain("UserPoolDomain", {
      cognitoDomain: { domainPrefix: props.cognitoDomainPrefix },
    });

    // Googleクライアントシークレットの実値は、私がGoogle Cloudでクライアントを作成した後、
    // AWSコンソール/CLIでこのシークレットに投入する（値をコードやgitに置かない）。
    this.googleOAuthClientSecret = new secretsmanager.Secret(
      this,
      "GoogleOAuthClientSecret",
      {
        secretName: "flourish/google-oauth-client-secret",
        description:
          "Google Cloud OAuthクライアントシークレット（P1-5。値は手動投入）",
      },
    );

    // シークレットの実値はSecretsManagerに手動投入済み（値はコード・gitに置かない）。
    const googleIdp = new cognito.UserPoolIdentityProviderGoogle(
      this,
      "GoogleIdentityProvider",
      {
        userPool: this.userPool,
        clientId: props.googleClientId,
        clientSecretValue: cdk.SecretValue.secretsManager(
          this.googleOAuthClientSecret.secretArn,
        ),
        scopes: ["openid", "email", "profile"],
        attributeMapping: {
          email: cognito.ProviderAttribute.GOOGLE_EMAIL,
        },
      },
    );

    this.userPoolClient = this.userPool.addClient("UserPoolClient", {
      generateSecret: true,
      // ログイン(P3-2)は`AdminInitiateAuth`の`ADMIN_USER_PASSWORD_AUTH`フローを使う
      // (サーバーサイド実行と親和性が高いAdmin*系APIに揃える判断。cognito.ts参照)。
      // CDKの既定値には含まれないため明示的に有効化する。
      authFlows: { adminUserPassword: true },
      oAuth: {
        flows: { authorizationCodeGrant: true },
        scopes: [
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.PROFILE,
        ],
        // API GatewayへはCloudFrontの`/api/v1/*`ビヘイビアが振り分ける(P1-7)ため、
        // コールバックパスにも`/api/v1`が要る(P3-3で発見・修正)。
        callbackUrls: [`https://${props.domainName}/api/v1/auth/google/callback`],
      },
      supportedIdentityProviders: [
        cognito.UserPoolClientIdentityProvider.COGNITO,
        cognito.UserPoolClientIdentityProvider.GOOGLE,
      ],
    });
    this.userPoolClient.node.addDependency(googleIdp);

    new cdk.CfnOutput(this, "UserPoolId", { value: this.userPool.userPoolId });
    new cdk.CfnOutput(this, "UserPoolClientId", {
      value: this.userPoolClient.userPoolClientId,
    });
    new cdk.CfnOutput(this, "CognitoDomainUrl", {
      value: `https://${props.cognitoDomainPrefix}.auth.${this.region}.amazoncognito.com`,
    });
    new cdk.CfnOutput(this, "GoogleRedirectUriToRegister", {
      description:
        "Google CloudのOAuthクライアントに登録する承認済みリダイレクトURI",
      value: `https://${props.cognitoDomainPrefix}.auth.${this.region}.amazoncognito.com/oauth2/idpresponse`,
    });
  }
}
