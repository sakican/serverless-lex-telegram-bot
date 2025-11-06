import json
import boto3
import os
import urllib.request
from datetime import datetime, timezone, timedelta
import time

lex_client = boto3.client("lexv2-runtime")
dynamodb = boto3.resource("dynamodb")
logs_table = dynamodb.Table(os.environ["LOGS_TABLE_NAME"])  # Logs table name from environment variable

BOT_ID = os.environ.get("LEX_BOT_ID")
BOT_ALIAS_ID = os.environ.get("LEX_BOT_ALIAS_ID")
BOT_LOCALE_ID = os.environ.get("LEX_LOCALE_ID", "en_US")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # Telegram Bot Token

def lambda_handler(event, context):
    for record in event.get("Records", []):
        print(f"SQS event: {record}")

        body_str = record.get("body", "")
        try:
            body = json.loads(body_str)
        except json.JSONDecodeError:
            print(f"Invalid JSON in SQS body: {body_str}")
            continue

        user_id = str(body.get("chat_id", "anonymous"))
        text = body.get("text", "")

        print(f"Received from SQS: {text}")

        # ----------------------------
        # Send text to Amazon Lex
        # ----------------------------
        reply_text = ""
        try:
            lex_response = lex_client.recognize_text(
                botId=BOT_ID,
                botAliasId=BOT_ALIAS_ID,
                localeId=BOT_LOCALE_ID,
                sessionId=user_id,
                text=text
            )
            print("Lex response:", json.dumps(lex_response))

            if "messages" in lex_response:
                reply_text = " ".join([m.get("content", "") for m in lex_response["messages"]])

            if reply_text:
                # Send reply back to Telegram
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                data = {"chat_id": user_id, "text": reply_text}
                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req)
                print(f"Sent to Telegram: {reply_text}")

        except Exception as e:
            print("Error calling Lex or Telegram:", str(e))
            reply_text = ""  # Even if failed, continue logging

        # ----------------------------
        # Save logs to DynamoDB
        # ----------------------------
        ttl_seconds = 60 * 60  # TTL = 60 minutes
        expire_at = int(time.time()) + ttl_seconds

        # UNIX timestamp (for numeric sorting or machine usage)
        unix_ts = int(time.time())

        # Human-readable timestamp (ISO8601)
        readable_ts = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")

        try:
            timestamp = datetime.utcnow().isoformat()
            logs_table.put_item(
                Item={
                    "user_id": user_id,
                    "timestamp": unix_ts,
                    "timestamp_str": readable_ts,
                    "input_message": text,
                    "bot_response": reply_text,
                    "expire_at": expire_at  # TTL attribute
                }
            )
            print(f"Saved log for user {user_id} at {timestamp}")
        except Exception as e:
            print("Error saving to Logs table:", str(e))

    return {"statusCode": 200}
