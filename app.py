from flask import Flask, jsonify, Response, request
from openai import OpenAI, AsyncOpenAI
import os
import json

import asyncio
import re
import requests
import threading
from queue import Queue, Empty
from functions.dalle import DALLE_FUNCTION

dummy_flag = True

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
generic_assistant = client.beta.assistants.retrieve(assistant_id='asst_pxYUpYo4Lg2miYZ4yWK9qmXn')


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
    has_images = False
    user_input = request.json.get('message', '')
    sessionID = request.headers.get("sessionID", "")
    userID = request.headers.get("userID", "")
    # get the thread if it exists for the sessionID, if not, initialize a new thread for the session
    if not sessionID:
        thread = client.beta.threads.create()
        THREADS_MAP[thread.id] = thread
    else:
        thread = THREADS_MAP[sessionID]
    if userID == 'sharon':
        assistant = sharon_bot_assistant
    elif userID == 'finn':
        assistant = finn_bot_assistant
    else:
        assistant = generic_assistant

    # Dummy flag to save costs for testing
    if dummy_flag and userID == 'sharon':
        dummy_content = {
            "path1": {
                "name": "Move back to Singapore", 
                "description": "If you choose to move back to Singapore, in 20 years, you'll find yourself deeply integrated into the rich cultural tapestry that defines the city-state. Your home is filled with the aromas of local cuisines you've mastered over the years. Family gatherings are a weekly highlight, where laughter and stories fill the air. Professionally, you've carved out a niche in Singapore's burgeoning tech scene, leveraging your international experience to foster connections and innovations that bridge East and West. The sense of belonging and the close-knit community you've built around you are your greatest sources of happiness.",
                "image_urls": ["https://crossroadsbucket.s3.us-west-2.amazonaws.com/path1%3A-3314722688263737280.png","https://crossroadsbucket.s3.us-west-2.amazonaws.com/path1%3A-8584559003477515054.png", "https://crossroadsbucket.s3.us-west-2.amazonaws.com/path1%3A2296003398307106680.png", "https://crossroadsbucket.s3.us-west-2.amazonaws.com/path1%3A7976919207731705464.png"],
                },
            "path2": {
                "name": "Stay in San Francisco", 
                "description": "On the other hand, should you choose to stay in the Bay Area, 20 years from now, you'll find yourself living in a cozy, technology-filled home in a quiet, leafy suburb close to the heart of Silicon Valley. You've made a significant impact in the tech industry, leading initiatives that have shaped the future of technology. While your career is fulfilling and your social life vibrant, there's a lingering sense of nostalgia for the familial closeness and cultural richness of Singapore. Despite this, the opportunities you've seized and the life you've built in the Bay Area have molded you into a globally respected leader, cherished friend, and a pioneer in your field.",
                "image_urls": ["https://crossroadsbucket.s3.us-west-2.amazonaws.com/path2%3A-5677335532780567126.png", "https://crossroadsbucket.s3.us-west-2.amazonaws.com/path2%3A-7719549257588876346.png", "https://crossroadsbucket.s3.us-west-2.amazonaws.com/path2%3A4056449266245581403.png", "https://crossroadsbucket.s3.us-west-2.amazonaws.com/path2%3A4384264233050141296.png"],
                }
        }
        conversation_json = {"id": -1,
                            "sessionID": sessionID or thread.id,
                            "role": "assistant",
                            "content_type": "text",
                            "content": dummy_content
                            }
        return Response(json.dumps(conversation_json))

    # Post the user message to the assistant
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
        tools=[{"type": "retrieval"}, DALLE_FUNCTION],
    )
    print(f"Run status: {run.status}")
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )

    if run.status == "requires_action":
        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        outputs=[]
        for tool_call in tool_calls:
            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            if name == "getDalleImages" and "prompt" in arguments:
                has_images = True
                url, path_num = getDalleImages(arguments["prompt"], arguments["path_num"])
                outputs.append({"tool_call_id": tool_call.id, "output": (f"Path: {path_num}", url)})
        run = client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread.id,
            run_id=run.id,
            tool_outputs=outputs,
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
            for content in message.content:
                conversation_output.append({"id": message.id,
                                            "sessionID": message.thread_id,
                                            "role": message.role,
                                            "content_type": content.type,
                                            "content": _parse_message(content.text.value, has_images),
                                            })
        else:
            break
    # serialize json before sending over the wire
    conversation_json = json.dumps(conversation_output)
    return Response(conversation_json)
    # send it over in chunks
    # return Response(generate_stream(conversation_json))

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
        return jsonify({'response': str(response.choices[0].message.content)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def getDalleImages(prompt: str, path_num: str):
    print(f"Calling DALL-E for prompt: {prompt}, path: {path_num}")
    generation_response = client.images.generate(
        model = "dall-e-3",
        style="vivid",
        prompt=prompt,
        n=1,
        size="1024x1024",
        response_format="url",
    )
    generated_image_name = f"{hash(prompt)}.png"
    generated_image_url = generation_response.data[0].url
    generated_image = requests.get(generated_image_url).content

    # Optional: Save locally
    image_dir_name = "images"
    image_dir = os.path.join(os.curdir, image_dir_name)
    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)
    generated_image_filepath = os.path.join(image_dir, generated_image_name)
    with open(generated_image_filepath, "wb") as image_file:
        image_file.write(generated_image)

    return generated_image_url, path_num

# The same message may include the 2 paths and the image(s)
# Or the images could be in their own message

def _parse_message(message, has_images):
    print(f"Parsing message: {message}")
    pattern = r'\n\n(.*?)\n\n'
    matches = re.findall(pattern, message)
    output = message
    if matches and len(matches) == 2:
        parts = re.split(pattern, message)
        # The descriptions should be in the parts after the matches
        path1_description = parts[2].strip() if len(parts) > 2 else ""
        path2_description = parts[4].strip() if len(parts) > 4 else ""
        output = {
            "path1": {"name": matches[0], "description": path1_description},
            "path2": {"name": matches[1], "description": path2_description}
        }
        if has_images:
            image_url_pattern = r'\!\[.*?\]\((.*?)\)'
            path1_images = re.findall(image_url_pattern, path1_description)
            path2_images = re.findall(image_url_pattern, path2_description)
            if path1_images:
                output["path1"]["image_urls"] = path1_images
            if path2_images:
                output["path2"]["image_urls"] = path2_images
    return output

if __name__ == '__main__':
    app.run(debug=True, threaded=True)