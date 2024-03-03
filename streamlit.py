from openai import OpenAI
import streamlit as st
import json
from utilities import save_image


st.set_page_config(page_title="The Crossroads v0.0.1", initial_sidebar_state="auto", page_icon="🎌", layout="wide", menu_items=None)
st.title("🎌 The Crossroads: Prototype v0.0.1")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
ASST_PROMPT = "I need help making a decision."

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

st.session_state["user_name"] = st.text_input("What's your name?")
file = st.file_uploader("Upload a document representing your life right now (pdf, docx, txt)", type=["pdf", "docx", "txt"])
if file:
    file_ref = client.files.create(file=file, purpose='assistants')
    assistant = client.beta.assistants.create(
        name=f"{st.session_state['user_name']} Bot",
        instructions=f"You are a bot meant to be a representation of a physical person {st.session_state['user_name']}. Engage with the user with the assumption that you and the user are both versions of them (one digital, and one physical). Help the user make the best possible life decision based on your knowledge of who they are and who they want to become: relationships, hobbies, central characteristics/ values, and more. When they ask a question, tell them what their life could look like 20 years in the future if they go on either of 2 paths. Respond in two paragraphs - one that follows the first path, and one that follows the second path. Paint a vivid picture: how does the user look and feel? Where do they live? What does their home look, sound, and smell like? What are their key memories of the past 20 years? How do they spend their spare time? Who and what do they love most in life? What topics are most important and dear to them? Respond to all of these questions, and remember - show the user what their life would look like based on each path. Then, give them a recommendation based on what you know their long-term goals are. Remember, your answer should have three parts: what their life would look like going down path 1 (very vivid), what their life would look like going down path 2 (also very vivid), and your recommendation (path 1 or path 2). Make sure your recommendation is centered around one path only, not multiple paths; you must give a concrete recommendation.",
        model="gpt-3.5-turbo-1106",
        tools=[{"type": "retrieval"}],
        file_ids=[file_ref.id],
    )
    st.session_state["user_assistant"] = assistant.id

    asst_response = None
    st.session_state["prompt"] = st.text_area("Please tell me more about the decision you are facing")
    if st.session_state["prompt"]:
        with st.spinner("Consulting your fates..."):
            thread = client.beta.threads.create(
                messages=[{"role": "user", "content": st.session_state["prompt"]}])
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            while run.status == "queued" or run.status == "in_progress":
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id,
                )
            if run.status == "completed":
                messages = client.beta.threads.messages.list(thread_id = thread.id)
                asst_response = messages.data[0].content[0].text.value
                st.write(asst_response)
            
        with st.spinner("Creating prompts for images to help you visualize your future..."):
            try:
                response = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": f'You are a helpful assistant coming up with descriptive prompts that will be passed into DALL-E to help a user visualize their future. Below is a paragraph describing two possible paths for {st.session_state["user_name"]}. Generate 2 prompts per path and parse the paragraph, returning your response as a json object with the following structure: {{"path1": {{"name": "Short phrase summarizing path 1", "description": "Given description of path 1", "image_prompts": ["prompt1", "prompt2"]}}, "path2": {{"name": "Short phrase summarizing path 2", "description": "Given description of path 2", "image_prompts": ["prompt1", "prompt2"]}}}}. Paragraph: {asst_response}',
                        }
                    ],
                    model="gpt-4",
                    max_tokens=1000
                )
                content = response.choices[0].message.content
                content_obj = json.loads(content)
                print(content_obj)
                if "path1" in content_obj and "path2" in content_obj:
                    path1_name, path2_name = content_obj["path1"].get("name", "Path 1"), content_obj["path2"].get("name", "Path 2")
                    col1, col2 = st.columns([1,1], gap="small")
                    with col1:
                        st.header(path1_name)
                        if "description" in content_obj["path1"]:
                            st.subheader("Description")
                            st.write(content_obj["path1"]["description"])
                        if "image_prompts" in content_obj["path1"]:
                            st.subheader("Image Prompts")
                            for prompt in content_obj["path1"]["image_prompts"]:
                                st.write(prompt)
                    with col2:
                        st.header(path2_name)
                        if "description" in content_obj["path2"]:
                            st.subheader("Description")
                            st.write(content_obj["path2"]["description"])
                        if "image_prompts" in content_obj["path2"]:
                            st.subheader("Image Prompts")
                            for prompt in content_obj["path2"]["image_prompts"]:
                                st.write(prompt)
            
            except Exception as e:
                error = f"An error occurred: {e}"
                st.write(error)            

        with st.spinner("Generating images from prompts..."):
            col3, col4 = st.columns([1,1], gap="small")
            prompt1, prompt2 = content_obj["path1"]["image_prompts"][0], content_obj["path2"]["image_prompts"][0]
            try:
                image1 = client.images.generate(
                    prompt=prompt1,
                    model = "dall-e-3",
                    style="vivid",
                    size="1024x1024",
                    response_format="url"
                )
                image1_url = save_image(image1, prompt1)
                image2 = client.images.generate(
                    prompt=prompt2,
                    model = "dall-e-3",
                    style="vivid",
                    size="1024x1024",
                    response_format="url"
                )
                image2_url = save_image(image2, prompt2)
                with col3:
                    st.image(image1_url)
                with col4:
                    st.image(image2_url)
            except Exception as e:
                error = f"An error occurred: {e}"
                st.write(error)