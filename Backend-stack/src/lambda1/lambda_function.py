import boto3
import os
import json
import urllib.request
from datetime import datetime

sqs = boto3.client('sqs')
queue_url = os.environ['SQS_QUEUE_URL']

# DynamoDB
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(os.environ['USERS_TABLE_NAME'])

def lambda_handler(event, context):
    print("Raw event:", event)

    body = event.get("body")
    if not body:
        print("No body found in event")
        return {"statusCode": 200, "body": "No body received"}

    try:
        telegram_update = json.loads(body)
    except Exception as e:
        print("JSON decode error:", e)
        return {"statusCode": 200, "body": "Invalid JSON"}

    print("Telegram update:", telegram_update)

    chat_id = telegram_update.get("message", {}).get("chat", {}).get("id")
    message_text = telegram_update.get("message", {}).get("text", "")
    print("Message text:", message_text)

    # ------------------------------
    # DynamoDB Users table operations
    # ------------------------------
    try:
        response = users_table.get_item(Key={"user_id": str(chat_id)})
        user_exists = 'Item' in response

        now_iso = datetime.utcnow().isoformat()

        if not user_exists:
            users_table.put_item(
                Item={
                    "user_id": str(chat_id),
                    "last_seen": now_iso
                }
            )
            print(f"Created new user: {chat_id}")
        else:
            users_table.update_item(
                Key={"user_id": str(chat_id)},
                UpdateExpression="SET last_seen = :t",
                ExpressionAttributeValues={":t": now_iso}
            )
            print(f"Updated last_seen for user: {chat_id}")

    except Exception as e:
        print("Error updating Users table:", e)

    # ------------------------------
    # Send message to SQS
    # ------------------------------
    try:
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                "chat_id": chat_id,
                "text": message_text
            })
        )
        print("SQS response:", response)
    except Exception as e:
        print("Error while sending to SQS:", e)

        # Notify Telegram only if SQS send fails
        token = os.environ["TELEGRAM_TOKEN"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": "⚠️ Your message could not be processed. Please try again later."}
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req)
        except Exception as e2:
            print("Failed to send Telegram reply:", e2)

    return {"statusCode": 200, "body": "Processed"}
