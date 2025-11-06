import json
import os
import urllib.request

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  

def call_chatgpt(user_input: str) -> str:
    """
    Sample function to call the ChatGPT API (using urllib)
    """
    print("### ChatGPT request:", user_input)

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are Dumbledore in Harry Potter. Answer like him"},
            {"role": "user", "content": user_input}
            ]
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            resp_data = json.loads(response.read().decode("utf-8"))
            # Check if successful response
            if "choices" in resp_data:
                return resp_data["choices"][0]["message"]["content"]
            elif "error" in resp_data:
                return f"OpenAI API error: {resp_data['error'].get('message', 'Unknown error')}"
            else:
                return "Unexpected response format from OpenAI API."
    except Exception as e:
        print("Error calling OpenAI:", str(e))
        return f"Sorry, I could not get a response from ChatGPT. Error: {str(e)}"

def echo_message(user_input: str) -> str:
    #Return user input as-is
    return f"You said: {user_input}"

def lambda_handler(event, context):
    print("Incoming event:", json.dumps(event))

    intent = event["sessionState"]["intent"]["name"]
    user_input = event.get("inputTranscript", "")

    print("### Identified intent:", intent)
    print("### User input:", user_input)

    if intent == "AskProfessor":
        print("### Calling ChatGPT API ###")
        answer = call_chatgpt(user_input)
    elif intent == "FallbackIntent":
        print("### Fallback triggered (echo) ###")
        answer = echo_message(user_input)
    else:
        print("### Unknown intent:", intent)
        answer = "Sorry, I couldn't understand that.hahaha"

    print("### Final answer to Lex:", answer)

    # Response format for Lex V2
    return {
        "sessionState": {
            "dialogAction": {"type": "Close"},
            "intent": {"name": intent, "state": "Fulfilled"}
        },
        "messages": [
            {"contentType": "PlainText", "content": answer}
        ]
    }
