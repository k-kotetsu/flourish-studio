import * as cdk from "aws-cdk-lib/core";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as cr from "aws-cdk-lib/custom-resources";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as targets from "aws-cdk-lib/aws-route53-targets";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as wafv2 from "aws-cdk-lib/aws-wafv2";
import { Construct } from "constructs";

// WAFのレート制限(IP単位、5分あたり)。技術構成4.5。
// RateBasedStatementのLimitはAWS側の制約で100が最小値のため、
// 「/api/v1/auth/*への厳しめの制限」も100とする(全体は1,000)。
const RATE_LIMIT_ALL = 1000;
const RATE_LIMIT_AUTH = 100;

// 長期キャッシュの期間(ハッシュ付きファイル・ビルド時アセット)。技術構成4.1。
const LONG_CACHE_TTL = cdk.Duration.days(365);
// 公開サイト("/" "/articles/*")のキャッシュTTL。技術構成4.1。
const PUBLIC_SITE_CACHE_TTL = cdk.Duration.hours(1);

export interface EdgeStackProps extends cdk.StackProps {
  /** SPAが表示される独自ドメイン(例: dev.flourish-st.com) */
  readonly domainName: string;
  /** ACM証明書を検索する際のドメイン名(apex。例: flourish-st.com) */
  readonly certificateDomainName: string;
  readonly hostedZoneId: string;
  readonly hostedZoneName: string;
  /** /api/v1/* の転送先(AppStack.api) */
  readonly api: apigateway.RestApi;
}

/**
 * P1-3で手動作成済みのACM証明書(us-east-1、ISSUED)をドメイン名で検索する。
 * ACMのListCertificatesはドメイン名での絞り込みに対応していないため、
 * 自前のカスタムリソースで一覧を取得してフィルタする。
 */
function lookupCertificateArn(
  scope: Construct,
  certificateDomainName: string,
): string {
  const onEvent = new lambda.Function(scope, "CertificateLookupHandler", {
    runtime: lambda.Runtime.NODEJS_24_X,
    architecture: lambda.Architecture.ARM_64,
    handler: "index.handler",
    timeout: cdk.Duration.seconds(30),
    code: lambda.Code.fromInline(`
      const { ACMClient, ListCertificatesCommand } = require("@aws-sdk/client-acm");

      exports.handler = async (event) => {
        if (event.RequestType === "Delete") {
          return {};
        }
        const domainName = event.ResourceProperties.DomainName;
        const client = new ACMClient({});
        let nextToken;
        let found;
        do {
          const res = await client.send(
            new ListCertificatesCommand({
              CertificateStatuses: ["ISSUED"],
              NextToken: nextToken,
            }),
          );
          found = (res.CertificateSummaryList ?? []).find(
            (c) => c.DomainName === domainName,
          );
          nextToken = res.NextToken;
        } while (!found && nextToken);
        if (!found) {
          throw new Error("ISSUEDな証明書が見つかりません: " + domainName);
        }
        return {
          PhysicalResourceId: found.CertificateArn,
          Data: { CertificateArn: found.CertificateArn },
        };
      };
    `),
  });
  onEvent.addToRolePolicy(
    new iam.PolicyStatement({
      actions: ["acm:ListCertificates"],
      resources: ["*"],
    }),
  );

  const provider = new cr.Provider(scope, "CertificateLookupProvider", {
    onEventHandler: onEvent,
  });

  const certificateLookup = new cdk.CustomResource(scope, "CertificateLookup", {
    serviceToken: provider.serviceToken,
    properties: { DomainName: certificateDomainName },
  });

  return certificateLookup.getAttString("CertificateArn");
}

export class EdgeStack extends cdk.Stack {
  readonly publicSiteBucket: s3.Bucket;
  readonly spaBucket: s3.Bucket;
  readonly distribution: cloudfront.Distribution;
  readonly webAcl: wafv2.CfnWebACL;

  constructor(scope: Construct, id: string, props: EdgeStackProps) {
    super(scope, id, props);

    // ビルド成果物であり真実の源ではないため、DBと違い保持保護は課さない(技術構成4.4)。
    const bucketDefaults = {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    };

    // "/" "/articles/*" "/assets/*"(技術構成4.1、4.4)。
    this.publicSiteBucket = new s3.Bucket(this, "PublicSiteBucket", bucketDefaults);
    // "/app/*"(技術構成4.1)。
    this.spaBucket = new s3.Bucket(this, "SpaBucket", bucketDefaults);

    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, "HostedZone", {
      hostedZoneId: props.hostedZoneId,
      zoneName: props.hostedZoneName,
    });

    const certificateArn = lookupCertificateArn(this, props.certificateDomainName);
    const certificate = acm.Certificate.fromCertificateArn(this, "Certificate", certificateArn);

    // "/app/*" 配下でS3に該当ファイルがない場合、index.htmlへ書き換える(技術構成4.2)。
    // S3のエラードキュメント設定は使わない(404とSPAルーティングが食い違うため)。
    const spaRoutingFunction = new cloudfront.Function(this, "SpaRoutingFunction", {
      code: cloudfront.FunctionCode.fromInline(`
        function handler(event) {
          var request = event.request;
          var uri = request.uri;
          if (!uri.split('/').pop().includes('.')) {
            request.uri = '/app/index.html';
          }
          return request;
        }
      `),
    });

    // 公開サイト("/" "/articles/*")はTTL1時間(技術構成4.1)。
    const publicSiteCachePolicy = new cloudfront.CachePolicy(this, "PublicSiteCachePolicy", {
      defaultTtl: PUBLIC_SITE_CACHE_TTL,
      minTtl: cdk.Duration.seconds(0),
      maxTtl: PUBLIC_SITE_CACHE_TTL,
    });

    // "/assets/*" はビルド時生成の長期キャッシュ(技術構成4.1)。
    const longCachePolicy = new cloudfront.CachePolicy(this, "LongCachePolicy", {
      defaultTtl: LONG_CACHE_TTL,
      minTtl: cdk.Duration.seconds(0),
      maxTtl: LONG_CACHE_TTL,
    });

    const publicSiteOrigin = origins.S3BucketOrigin.withOriginAccessControl(this.publicSiteBucket);
    const spaOrigin = origins.S3BucketOrigin.withOriginAccessControl(this.spaBucket);
    const apiOrigin = new origins.RestApiOrigin(props.api);

    this.webAcl = new wafv2.CfnWebACL(this, "WebAcl", {
      scope: "CLOUDFRONT",
      defaultAction: { allow: {} },
      visibilityConfig: {
        sampledRequestsEnabled: true,
        cloudWatchMetricsEnabled: true,
        metricName: "flourish-edge-webacl",
      },
      rules: [
        {
          name: "AWSManagedRulesCommonRuleSet",
          priority: 0,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: "AWS",
              name: "AWSManagedRulesCommonRuleSet",
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: "AWSManagedRulesCommonRuleSet",
          },
        },
        {
          name: "RateLimitAll",
          priority: 1,
          action: { block: {} },
          statement: {
            rateBasedStatement: {
              limit: RATE_LIMIT_ALL,
              aggregateKeyType: "IP",
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: "RateLimitAll",
          },
        },
        {
          // 総当たり対策(技術構成4.5)。
          name: "RateLimitAuth",
          priority: 2,
          action: { block: {} },
          statement: {
            rateBasedStatement: {
              limit: RATE_LIMIT_AUTH,
              aggregateKeyType: "IP",
              scopeDownStatement: {
                byteMatchStatement: {
                  searchString: "/api/v1/auth/",
                  fieldToMatch: { uriPath: {} },
                  textTransformations: [{ priority: 0, type: "NONE" }],
                  positionalConstraint: "STARTS_WITH",
                },
              },
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: "RateLimitAuth",
          },
        },
      ],
    });

    this.distribution = new cloudfront.Distribution(this, "Distribution", {
      domainNames: [props.domainName],
      certificate,
      webAclId: this.webAcl.attrArn,
      defaultRootObject: "index.html",
      defaultBehavior: {
        // "/" (技術構成4.1)。
        origin: publicSiteOrigin,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: publicSiteCachePolicy,
      },
      additionalBehaviors: {
        "/api/v1/*": {
          origin: apiOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER,
          // 圧縮を挟むとバッファされ、SSEの逐次配信が壊れる可能性がある(技術構成4.3)。
          compress: false,
        },
        "/app/*": {
          origin: spaOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
          functionAssociations: [
            {
              function: spaRoutingFunction,
              eventType: cloudfront.FunctionEventType.VIEWER_REQUEST,
            },
          ],
        },
        "/articles/*": {
          origin: publicSiteOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: publicSiteCachePolicy,
        },
        "/assets/*": {
          origin: publicSiteOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: longCachePolicy,
        },
      },
    });

    new route53.ARecord(this, "AliasRecord", {
      zone: hostedZone,
      recordName: props.domainName,
      target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(this.distribution)),
    });

    new cdk.CfnOutput(this, "DistributionDomainName", {
      value: this.distribution.distributionDomainName,
    });
    new cdk.CfnOutput(this, "PublicSiteBucketName", { value: this.publicSiteBucket.bucketName });
    new cdk.CfnOutput(this, "SpaBucketName", { value: this.spaBucket.bucketName });
  }
}
