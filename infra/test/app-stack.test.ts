import * as cdk from "aws-cdk-lib/core";
import { Template } from "aws-cdk-lib/assertions";
import { AppStack } from "../lib/app-stack";

function synth(): Template {
  const app = new cdk.App();
  const stack = new AppStack(app, "AppStack", {
    env: { account: "123456789012", region: "ap-northeast-1" },
  });
  return Template.fromStack(stack);
}

describe("AppStack", () => {
  it("Lambdaを2つ(APIとワーカー)持つ", () => {
    const template = synth();
    const functions = template.findResources("AWS::Lambda::Function");
    expect(Object.keys(functions)).toHaveLength(2);
  });

  it("ワーカーLambdaだけ予約同時実行を5に設定する(技術構成5.3)", () => {
    const template = synth();
    const functions = Object.values(template.findResources("AWS::Lambda::Function"));
    const reservedConcurrencies = functions
      .map((fn) => fn.Properties.ReservedConcurrentExecutions)
      .filter((v) => v !== undefined);
    expect(reservedConcurrencies).toEqual([5]);
  });

  it("ジョブキューはDLQ付きでmaxReceiveCount=1(自動リトライしない。技術構成5.5)", () => {
    const template = synth();
    template.hasResourceProperties("AWS::SQS::Queue", {
      QueueName: "flourish-job-queue",
      VisibilityTimeout: 330,
      RedrivePolicy: {
        maxReceiveCount: 1,
      },
    });
    template.hasResourceProperties("AWS::SQS::Queue", {
      QueueName: "flourish-job-dlq",
    });
  });

  it("APIのMethodはResponseTransferMode: STREAMを持つ(技術構成5.2)", () => {
    const template = synth();
    const methods = Object.values(template.findResources("AWS::ApiGateway::Method"));
    const withStream = methods.filter(
      (m) => m.Properties.Integration?.ResponseTransferMode === "STREAM",
    );
    expect(withStream.length).toBeGreaterThan(0);
    for (const method of withStream) {
      const uri = JSON.stringify(method.Properties.Integration.Uri);
      expect(uri).toContain("response-streaming-invocations");
    }
  });

  it("BedrockのIAM権限はResource: \"*\" にしない(技術構成8.5)", () => {
    const template = synth();
    const policies = Object.values(template.findResources("AWS::IAM::Policy"));
    const bedrockStatements = policies.flatMap((policy) =>
      policy.Properties.PolicyDocument.Statement.filter((statement: { Action?: unknown }) => {
        const actions = Array.isArray(statement.Action) ? statement.Action : [statement.Action];
        return actions.some((a: string) => typeof a === "string" && a.startsWith("bedrock:"));
      }),
    );
    expect(bedrockStatements.length).toBeGreaterThan(0);
    for (const statement of bedrockStatements) {
      expect(statement.Resource).not.toBe("*");
    }
  });
});
