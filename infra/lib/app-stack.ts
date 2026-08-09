import * as path from "path";
import * as cdk from "aws-cdk-lib/core";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import * as sqs from "aws-cdk-lib/aws-sqs";
import { Construct } from "constructs";

// Bedrockで呼ぶモデルだけを許可する(技術構成8.5)。Resource: "*" にしない。
// クロスリージョン推論プロファイル経由の呼び出しには、プロファイル自体に加えて
// 実行先となりうる各リージョンの基盤モデルARNへの許可も要る(P0-3で実機確認)。
const BEDROCK_MODEL_IDS = ["anthropic.claude-sonnet-5", "anthropic.claude-haiku-4-5-20251001-v1:0"];
const BEDROCK_INFERENCE_PROFILE_REGION = "us-east-1";
const BEDROCK_MODEL_REGIONS = ["us-east-1", "us-east-2", "us-west-2"];

function bedrockModelResourceArns(account: string): string[] {
  const arns: string[] = [];
  for (const modelId of BEDROCK_MODEL_IDS) {
    arns.push(
      `arn:aws:bedrock:${BEDROCK_INFERENCE_PROFILE_REGION}:${account}:inference-profile/us.${modelId}`,
    );
    for (const region of BEDROCK_MODEL_REGIONS) {
      arns.push(`arn:aws:bedrock:${region}::foundation-model/${modelId}`);
    }
  }
  return arns;
}

export class AppStack extends cdk.Stack {
  readonly api: apigateway.RestApi;
  readonly queue: sqs.Queue;
  readonly deadLetterQueue: sqs.Queue;
  readonly apiFunction: lambda.DockerImageFunction;
  readonly workerFunction: lambda.DockerImageFunction;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const apiAssetDir = path.join(__dirname, "..", "..", "api");

    // DLQは保持14日でアラーム対象(技術構成11.1)。
    this.deadLetterQueue = new sqs.Queue(this, "JobDeadLetterQueue", {
      queueName: "flourish-job-dlq",
      retentionPeriod: cdk.Duration.days(14),
    });

    // maxReceiveCount=1: 自動リトライしない(技術構成5.5)。
    // 失敗はユーザーに見せ、押されたときだけ再実行する(破ってはいけない規則5)。
    this.queue = new sqs.Queue(this, "JobQueue", {
      queueName: "flourish-job-queue",
      visibilityTimeout: cdk.Duration.seconds(330),
      deadLetterQueue: {
        queue: this.deadLetterQueue,
        maxReceiveCount: 1,
      },
    });

    // API Lambda: 1,024MB / 120秒 / 予約同時実行なし(技術構成5.3)。
    this.apiFunction = new lambda.DockerImageFunction(this, "ApiFunction", {
      code: lambda.DockerImageCode.fromImageAsset(apiAssetDir, { file: "Dockerfile" }),
      architecture: lambda.Architecture.ARM_64,
      memorySize: 1024,
      timeout: cdk.Duration.seconds(120),
    });

    // ワーカーLambda: 1,769MB / 300秒 / 予約同時実行5(Bedrockのスロットリング対策。技術構成5.3)。
    this.workerFunction = new lambda.DockerImageFunction(this, "WorkerFunction", {
      code: lambda.DockerImageCode.fromImageAsset(apiAssetDir, { file: "Dockerfile.worker" }),
      architecture: lambda.Architecture.ARM_64,
      memorySize: 1769,
      timeout: cdk.Duration.seconds(300),
      reservedConcurrentExecutions: 5,
    });
    this.workerFunction.addEventSource(
      new lambdaEventSources.SqsEventSource(this.queue, { batchSize: 1 }),
    );

    const bedrockPolicy = new iam.PolicyStatement({
      actions: ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      resources: bedrockModelResourceArns(this.account),
    });
    this.apiFunction.addToRolePolicy(bedrockPolicy);
    this.workerFunction.addToRolePolicy(bedrockPolicy);

    this.api = new apigateway.LambdaRestApi(this, "Api", {
      handler: this.apiFunction,
      proxy: true,
      deployOptions: { stageName: "prod" },
    });

    // API GatewayがlambdaのInvokeWithResponseStreamを呼べるようにする。
    // LambdaRestApiが自動付与するのはlambda:InvokeFunctionのみで、
    // ResponseTransferMode: STREAMのMethodには別途この権限が要る(P0-3で実機確認)。
    this.apiFunction.addPermission("ApiGatewayInvokeWithResponseStream", {
      principal: new iam.ServicePrincipal("apigateway.amazonaws.com"),
      action: "lambda:InvokeWithResponseStream",
      sourceArn: this.api.arnForExecuteApi(),
    });

    // API GatewayのSTREAM対応はL2未対応のためエスケープハッチで指定する。
    // ResponseTransferModeはMethod直下ではなくMethod.Integration配下のプロパティで、
    // 統合URIもInvokeWithResponseStream専用の
    // /2021-11-15/functions/{arn}/response-streaming-invocations に変える必要がある
    // (技術構成5.2。P0-3でCDKコード例の誤りを実機で発見・修正した)。
    const streamingInvocationUri = `arn:aws:apigateway:${this.region}:lambda:path/2021-11-15/functions/${this.apiFunction.functionArn}/response-streaming-invocations`;
    for (const method of this.api.methods) {
      const cfnMethod = method.node.defaultChild as apigateway.CfnMethod;
      cfnMethod.addPropertyOverride("Integration.ResponseTransferMode", "STREAM");
      cfnMethod.addPropertyOverride("Integration.Uri", streamingInvocationUri);
    }

    new cdk.CfnOutput(this, "ApiUrl", { value: this.api.url });
    new cdk.CfnOutput(this, "JobQueueUrl", { value: this.queue.queueUrl });
    new cdk.CfnOutput(this, "JobDeadLetterQueueUrl", { value: this.deadLetterQueue.queueUrl });
  }
}
