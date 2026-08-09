import * as cdk from "aws-cdk-lib/core";
import { Template } from "aws-cdk-lib/assertions";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { EdgeStack } from "../lib/edge-stack";

function synth(): Template {
  const app = new cdk.App();

  // EdgeStackはapiプロパティにAppStackのRestApiを要求するが、
  // ここではDocker資産を避けるため最小限のRestApiで代替する。
  const apiHostStack = new cdk.Stack(app, "ApiHostStack", {
    env: { account: "123456789012", region: "ap-northeast-1" },
    crossRegionReferences: true,
  });
  const dummyFn = new lambda.Function(apiHostStack, "DummyFunction", {
    runtime: lambda.Runtime.NODEJS_24_X,
    handler: "index.handler",
    code: lambda.Code.fromInline("exports.handler = async () => ({ statusCode: 200 });"),
  });
  const api = new apigateway.LambdaRestApi(apiHostStack, "Api", { handler: dummyFn });

  const stack = new EdgeStack(app, "EdgeStack", {
    env: { account: "123456789012", region: "us-east-1" },
    crossRegionReferences: true,
    domainName: "dev.flourish-st.com",
    certificateDomainName: "flourish-st.com",
    hostedZoneId: "Z0416565YMZIN1UIDKI5",
    hostedZoneName: "flourish-st.com",
    api,
  });
  return Template.fromStack(stack);
}

describe("EdgeStack", () => {
  it("S3バケットを2つ(公開サイト用・SPA用)持ち、パブリックアクセスをブロックする(技術構成2章、4.1)", () => {
    const template = synth();
    const buckets = template.findResources("AWS::S3::Bucket");
    expect(Object.keys(buckets)).toHaveLength(2);
    for (const bucket of Object.values(buckets)) {
      expect(bucket.Properties.PublicAccessBlockConfiguration).toEqual({
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      });
      // S3のエラードキュメント設定は使わない(技術構成4.2)。
      expect(bucket.Properties.WebsiteConfiguration).toBeUndefined();
    }
  });

  it("CloudFrontが4ビヘイビア(デフォルト＋/api/v1/*、/app/*、/articles/*、/assets/*)を持つ(技術構成4.1)", () => {
    const template = synth();
    const distributions = Object.values(
      template.findResources("AWS::CloudFront::Distribution"),
    );
    expect(distributions).toHaveLength(1);
    const config = distributions[0].Properties.DistributionConfig;
    expect(config.DefaultCacheBehavior).toBeDefined();
    const pathPatterns = (config.CacheBehaviors ?? []).map(
      (b: { PathPattern: string }) => b.PathPattern,
    );
    expect(pathPatterns.sort()).toEqual(["/api/v1/*", "/app/*", "/articles/*", "/assets/*"]);
  });

  it("/api/v1/* はキャッシュを無効化し、圧縮を無効にする(技術構成4.3)", () => {
    const template = synth();
    const distribution = Object.values(
      template.findResources("AWS::CloudFront::Distribution"),
    )[0];
    const config = distribution.Properties.DistributionConfig;
    const apiBehavior = (config.CacheBehaviors as Array<{ PathPattern: string }>).find(
      (b) => b.PathPattern === "/api/v1/*",
    ) as { Compress: boolean; CachePolicyId: unknown } | undefined;
    expect(apiBehavior).toBeDefined();
    expect(apiBehavior?.Compress).toBe(false);
    // CACHING_DISABLED の既定ポリシーID
    expect(apiBehavior?.CachePolicyId).toBe("4135ea2d-6df8-44a3-9df3-4b5a84be39ad");
  });

  it("WAFはCLOUDFRONTスコープで、Managed Rulesとレート制限を持つ(技術構成4.5)", () => {
    const template = synth();
    template.hasResourceProperties("AWS::WAFv2::WebACL", {
      Scope: "CLOUDFRONT",
    });
    const webAcls = Object.values(template.findResources("AWS::WAFv2::WebACL"));
    expect(webAcls).toHaveLength(1);
    const rules = webAcls[0].Properties.Rules as Array<{
      Name: string;
      Statement: { RateBasedStatement?: { Limit: number } };
    }>;
    const ruleNames = rules.map((r) => r.Name);
    expect(ruleNames).toEqual(
      expect.arrayContaining(["AWSManagedRulesCommonRuleSet", "RateLimitAll", "RateLimitAuth"]),
    );
    const rateLimitAll = rules.find((r) => r.Name === "RateLimitAll");
    const rateLimitAuth = rules.find((r) => r.Name === "RateLimitAuth");
    expect(rateLimitAll?.Statement.RateBasedStatement?.Limit).toBe(1000);
    // AWS WAFv2のLimitは100が最小値のため、「厳しめ」の実現可能な最小値を使う
    expect(rateLimitAuth?.Statement.RateBasedStatement?.Limit).toBe(100);
  });

  it("独自ドメインを指すRoute53エイリアスレコードを持つ", () => {
    const template = synth();
    template.hasResourceProperties("AWS::Route53::RecordSet", {
      Name: "dev.flourish-st.com.",
      Type: "A",
      HostedZoneId: "Z0416565YMZIN1UIDKI5",
    });
  });
});
