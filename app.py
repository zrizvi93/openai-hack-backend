from flask import Flask, jsonify, Response
from openai import OpenAI, AsyncOpenAI
import os

import asyncio
import threading
from queue import Queue, Empty

app = Flask(__name__)

client = AsyncOpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

def stream_gpt4_responses(queue):
    async def async_stream():
        stream = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "How are you today?"}],
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].message['content'] if chunk.choices else ""
            queue.put(content)
        queue.put(None)  # Signal the end of streaming

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(async_stream())

@app.route('/gpt4', methods=['GET'])
def gpt4_response():
    queue = Queue()
    def generate():
        t = threading.Thread(target=stream_gpt4_responses, args=(queue,))
        t.start()
        while True:
            try:
                data = queue.get(timeout=30)  # Adjust timeout as needed
                if data is None:  # Check if streaming is done
                    break
                yield data
            except Empty:
                break
        t.join()

    return Response(generate(), content_type='text/plain')

@app.route('/assistants', methods=['GET'])
def assistants_response():
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "How are you today?"}
            ]
        )
        return jsonify({'response': response.choices[0].message['content'].strip()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def hello_world():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True, threaded=True)