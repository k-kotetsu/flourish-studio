import * as cdk from "aws-cdk-lib/core";
import { Template } from "aws-cdk-lib/assertions";
import { DataStack } from "../lib/data-stack";

function synth(): Template {
  const app = new cdk.App();
  const stack = new DataStack(app, "DataStack", {
    env: { account: "123456789012", region: "ap-northeast-1" },
  });
  return Template.fromStack(stack);
}

describe("DataStack", () => {
  it("flourishテーブルはPK/SK・オンデマンド・TTL(expires_at)を持つ", () => {
    const template = synth();
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      TableName: "flourish",
      BillingMode: "PAY_PER_REQUEST",
      KeySchema: [
        { AttributeName: "PK", KeyType: "HASH" },
        { AttributeName: "SK", KeyType: "RANGE" },
      ],
      TimeToLiveSpecification: {
        AttributeName: "expires_at",
        Enabled: true,
      },
    });
  });

  it("flourish_articleテーブルはcategory-index GSIを持つ", () => {
    const template = synth();
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      TableName: "flourish_article",
      KeySchema: [{ AttributeName: "slug", KeyType: "HASH" }],
      GlobalSecondaryIndexes: [
        {
          IndexName: "category-index",
          KeySchema: [
            { AttributeName: "category", KeyType: "HASH" },
            { AttributeName: "published_at", KeyType: "RANGE" },
          ],
        },
      ],
    });
  });

  it("両テーブルとも削除保護・RETAIN・PITRが有効", () => {
    const template = synth();
    const tables = template.findResources("AWS::DynamoDB::Table");
    const names = Object.values(tables).map((t) => t.Properties.TableName);
    expect(names.sort()).toEqual(["flourish", "flourish_article"]);

    for (const resource of Object.values(tables)) {
      expect(resource.Properties.DeletionProtectionEnabled).toBe(true);
      expect(resource.DeletionPolicy).toBe("Retain");
      expect(resource.UpdateReplacePolicy).toBe("Retain");
      expect(
        resource.Properties.PointInTimeRecoverySpecification
          .PointInTimeRecoveryEnabled,
      ).toBe(true);
    }
  });
});
