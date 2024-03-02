from flask import Flask, jsonify, Response, request
from openai import OpenAI, AsyncOpenAI
import os
import json

import asyncio
import threading
from queue import Queue, Empty

app = Flask(__name__)

THREADS_MAP = {}

async_client = AsyncOpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

assistant = client.beta.assistants.create(
    name="Career Mentor",
    instructions="You are a career mentor. Answer questions briefly, in a sentence or less.",
    model="gpt-4-1106-preview",
)

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
            messages=[{"role": "user", "content": "Say this is a test"}],
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield str(chunk.choices[0].delta.content)
        # for chunk in stream:
        #     if chunk['choices'][0]['message']['content']:
        #         yield chunk['choices'][0]['message']['content']
    except Exception as e:
        yield str(e)  # Handle exceptions

@app.route('/conversation', methods=['POST'])
def conversation():
    user_input = request.json.get('message', '')
    return Response(generate_stream(user_input))


# def stream_gpt4_responses(queue):
#     async def async_stream():
#         stream = await client.chat.completions.create(
#             model="gpt-4",
#             messages=[{"role": "user", "content": "How are you today?"}],
#             stream=True,
#         )
#         async for chunk in stream:
#             content = chunk.choices[0].message['content'] if chunk.choices else ""
#             queue.put(content)
#         queue.put(None)  # Signal the end of streaming

#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(async_stream())

# @app.route('/gpt4async', methods=['GET'])
# def gpt4_async_response():
#     queue = Queue()
#     def generate():
#         t = threading.Thread(target=stream_gpt4_responses, args=(queue,))
#         t.start()
#         while True:
#             try:
#                 data = queue.get(timeout=30)  # Adjust timeout as needed
#                 if data is None:  # Check if streaming is done
#                     break
#                 yield data
#             except Empty:
#                 break
#         t.join()

#     return Response(generate(), content_type='text/plain')

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
        return jsonify({'response': response.choices[0].message}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/assistants', methods=['GET'])
def assistants_response():
    try:
        sessionID = request.headers.get("sessionID", "")
        # get the thread if it exists for the sessionID, if not, initialize a new thread for the session
        thread = THREADS_MAP.get(sessionID,client.beta.threads.create())
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="I need to solve the equation `3x + 11 = 14`. Can you help me?",
        )
        return "In Progress", 200
        # response = client.chat.completions.create(
        #     model="gpt-4",
        #     messages=[
        #         {"role": "system", "content": "You are a helpful assistant."},
        #         {"role": "user", "content": "How are you today?"}
        #     ]
        # )
        # return jsonify({'response': response.choices[0].message['content'].strip()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, threaded=True)