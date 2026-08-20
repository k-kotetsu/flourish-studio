/** dev/prodを同一AWSアカウント内で分離するための環境識別子(P7-10)。
 * DynamoDBテーブル名・SQSキュー名・Cognito User Pool名などの物理名のsuffixに使う
 * (同一アカウント・同一リージョンでは物理名が一意である必要があるため)。
 */
export type Stage = "dev" | "prod";
