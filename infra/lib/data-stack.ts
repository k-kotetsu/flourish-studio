import * as cdk from "aws-cdk-lib/core";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { Construct } from "constructs";

export class DataStack extends cdk.Stack {
  readonly table: dynamodb.Table;
  readonly articleTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    this.table = new dynamodb.Table(this, "FlourishTable", {
      tableName: "flourish",
      partitionKey: { name: "PK", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "SK", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.DEFAULT,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      timeToLiveAttribute: "expires_at",
      deletionProtection: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    this.articleTable = new dynamodb.Table(this, "FlourishArticleTable", {
      tableName: "flourish_article",
      partitionKey: { name: "slug", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.DEFAULT,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      deletionProtection: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    this.articleTable.addGlobalSecondaryIndex({
      indexName: "category-index",
      partitionKey: { name: "category", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "published_at", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });
  }
}
