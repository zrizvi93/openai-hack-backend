from flask import Flask, jsonify, Response, request
from openai import OpenAI, AsyncOpenAI
import os
import json

import asyncio
import threading
from queue import Queue, Empty

app = Flask(__name__)

THREADS_MAP = {}

# OpenAI Clients
async_client = AsyncOpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Assistants
sharon_bot_assistant = client.beta.assistants.retrieve(assistant_id='asst_MdVycnMtxDnpID4AFUVGucA1')
finn_bot_assistant = client.beta.assistants.retrieve(assistant_id='asst_J9iDe4fOUnS1FcMnOcGnn17f')
generic_assistant = client.beta.assistants.create(
    name="Career Mentor",
    instructions="You are a career mentor. Answer questions briefly, in a sentence or less.",
    model="gpt-4-1106-preview",
)


# App Routes

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/long_text', methods=['GET'])
def long_text():
    response_text = 'FAKE TEXT, FAKE TEXT FAKE TEXT FAKE TEXT FAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE\
          TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE\
            TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXTFAKE TEXT'
    return Response(response_text, content_type='text/plain')

def generate_stream(user_input):
    try:
        stream = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Give me a lengthy explanation of quantum physics"}],
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                print(str(chunk.choices[0].delta.content))
                yield str(chunk.choices[0].delta.content)
    except Exception as e:
        yield str(e)

@app.route('/conversation', methods=['POST'])
def conversation():
    assistant = None
    user_input = request.json.get('message', '')
    sessionID = request.headers.get("sessionID", "")
    userID = request.headers.get("userID", "")
    # get the thread if it exists for the sessionID, if not, initialize a new thread for the session
    thread = THREADS_MAP.get(sessionID, client.beta.threads.create())
    if userID == 'sharon':
        assistant = sharon_bot_assistant
    elif userID == 'finn':
        assistant = finn_bot_assistant
    else:
        assistant = generic_assistant

    # Post the user message to the asssitant
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input,
    )
    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        model="gpt-4-turbo-preview",
        tools=[{"type": "retrieval"}]
    )
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )

    # It's possible the assistant can post multiple messages
    # before the next user input
    messages = client.beta.threads.messages.list(
        thread_id=thread.id
        )
    conversation_output = []
    # Only want the most recent messages in the thread sent by the assistant
    for message in messages:
        if message.role != "user":
            conversation_output.append({"id": message.id,
                                        "sessionID": message.thread_id,
                                        "role": message.role,
                                        "content": message.content
                                        })
        else:
            break
    # serialize json before sending over the wire
    conversation_json = json.dumps(conversation_output)
    # send it over in chunks
    return Response(generate_stream(conversation_json))

# @app.route('/picture', methods=['GET'])
# def gpt4_response():
#     try:
#         response = client.chat.completions.create(
#             messages=[
#                 {
#                     "role": "user",
#                     "content": "Say this is a test",
#                 }
#             ],
#             model="gpt-3.5-turbo",
#             max_tokens=1000
#         )
#         return jsonify({'response': response.choices[0].message.content}), 200
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@app.route('/gpt4', methods=['GET'])
def gpt4_response():
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ],
            model="gpt-4-turbo-preview",
            max_tokens=1000
        )
        return jsonify({'response': response.choices[0].message.content}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, threaded=True)