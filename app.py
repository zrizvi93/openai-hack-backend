from flask import Flask, jsonify
import openai
import os

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/gpt4', methods=['GET'])
def gpt4_response():
    try:
        response = openai.Completion.create(
            model="gpt-4",
            prompt="How are you today?",
            max_tokens=1000,
        )
        return jsonify({'response': response.choices[0].text.strip()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/assistants', methods=['GET'])
def assistants_response():
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4", # Update this if you're using a different model
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
