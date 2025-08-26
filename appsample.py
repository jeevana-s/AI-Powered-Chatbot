# appsample.py

import streamlit as st
from PIL import Image
from fpdf import FPDF
from io import StringIO
import json
from backend import GenerateResponse
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException
import datetime
import re

# Page setup
st.set_page_config(page_title="Chatbot", page_icon="🧠", layout="wide")

# ------------------- Helpers -------------------
def load_users():
    try:
        with open('users.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_users(user_db):
    with open('users.json', 'w') as file:
        json.dump(user_db, file)

def download_text(messages):
    chat_content = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages])
    text_file = StringIO()
    text_file.write(chat_content)
    text_file.seek(0)
    return text_file.getvalue().encode('utf-8')

# --- REPLACED download_pdf FUNCTION ---
def download_pdf(messages):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for m in messages:
        # Sanitize the content to remove characters not supported by latin-1
        sanitized_content = m['content'].encode('latin-1', 'ignore').decode('latin-1')
        pdf.multi_cell(0, 10, f"{m['role'].capitalize()}: {sanitized_content}")
    return pdf.output(dest='S').encode('latin1')

def detect_language(text):
    try:
        return detect(text)
    except LangDetectException:
        return 'en'

def translate_text(text, target_lang='en'):
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception:
        return text

# ------------------- Response Generator -------------------
def response_generator(messages, image=None):
    last_user_msg = next((m for m in reversed(messages) if m["role"] == "user"), None)
    if not last_user_msg:
        return GenerateResponse("", image)

    user_text = last_user_msg["content"].lower()

    # Handle tomorrow date locally
    if "tomorrow" in user_text and "date" in user_text:
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        return f"Tomorrow's date is {tomorrow.strftime('%d-%m-%Y')}."

    # Handle explanation request (convert code to another language)
    explain_match = re.search(r'explain.*in\s+(\w+)', user_text)
    if explain_match:
        target_lang = explain_match.group(1).lower()
        last_code = None
        for msg in reversed(messages):
            if msg["role"] == "assistant" and "```" in msg["content"]:
                last_code = msg["content"]
                break
        if last_code:
            prompt = (
                f"Convert the following code to {target_lang} and explain it:\n"
                f"{last_code}\n"
                f"Please provide the code in {target_lang} with explanation."
            )
            return GenerateResponse(prompt, image)

    # Normal case → send conversation to Gemini
    # Filter out image data from the prompt to avoid sending it as text
    prompt_lines = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if content:
            prompt_lines.append(f"{role.capitalize()}: {content}")
    
    full_prompt = "\n".join(prompt_lines)
    return GenerateResponse(full_prompt, image)

# ------------------- Styling -------------------
st.markdown("""
    <style>
        .stTextInput>div>div>input {
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #ccc;
        }
        .stButton>button {
            background-color: #2ecc71;
            color: white;
            border-radius: 30px;
            padding: 8px 20px;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #27ae60;
            color: white;
        }
        /* Style for the image preview in the chat box */
        .image-preview {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 5px;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# ------------------- Global State -------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "page" not in st.session_state:
    st.session_state.page = "login"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "username" not in st.session_state:
    st.session_state.username = ""
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

user_db = load_users()

# ------------------- Login Page -------------------
def login_page():
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("## Login to Your Account")
        username = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", placeholder="Enter your password", type="password")

        if st.button("Login", use_container_width=True):
            stored_password = user_db.get(username)
            if stored_password and password == stored_password:
                st.success("Login successful!")
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.page = "chatbot"
                st.rerun()
            else:
                st.error("Invalid credentials")

    with col2:
        st.markdown("## New Here?")
        st.markdown("Sign up and discover a great amount of new opportunities!")
        if st.button("Sign Up", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()

# ------------------- Signup Page -------------------
def signup_page():
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("## ✍ Signup for Chatbot")
        new_username = st.text_input("Choose a username")
        new_password = st.text_input("Choose a password", type="password")

        if st.button("Create Account", use_container_width=True):
            if new_username in user_db:
                st.error("Username already exists.")
            else:
                user_db[new_username] = new_password
                save_users(user_db)
                st.success("Account created! Go to login.")
                st.session_state.page = "login"
                st.rerun()

    with col2:
        st.markdown("## Already have an account?")
        if st.button("Go to Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()

# ------------------- Chatbot Page -------------------
def chatbot_page():
    st.title("🧠 Chatbot")

    # Sidebar
    st.sidebar.title("Chat Options")
    if st.session_state.messages:
        st.sidebar.download_button("📄 Download Chat (Text)", download_text(st.session_state.messages), file_name="chat_history.txt")
        st.sidebar.download_button("📄 Download Chat (PDF)", download_pdf(st.session_state.messages), file_name="chat_history.pdf")
    else:
        st.sidebar.markdown("ℹ️ Start a chat to enable downloads.")

    if st.sidebar.button("🧹 Clear Chat & History"):
        st.session_state.messages.clear()
        st.session_state.uploader_key += 1
        st.session_state.uploaded_image = None
        st.rerun()

    if st.sidebar.button("🔒 Logout"):
        st.session_state.authenticated = False
        st.session_state.page = "login"
        st.rerun()

    uploaded_file = st.sidebar.file_uploader(
        "Upload an image (optional):", 
        type=["jpg", "jpeg", "png"], 
        key=f"image_uploader_{st.session_state.uploader_key}",
        label_visibility="collapsed"
    )

    if uploaded_file:
        st.session_state.uploaded_image = Image.open(uploaded_file)
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if 'image' in msg and msg['image']:
                st.image(msg['image'], caption="Uploaded Image", use_container_width=True)

    if st.session_state.uploaded_image and not st.session_state.messages:
        with st.chat_message("user"):
            st.markdown("Ready to send:")
            st.image(st.session_state.uploaded_image, caption="Uploaded Image", use_container_width=True)

    prompt = st.chat_input("Type your message...")

    if prompt or (st.session_state.uploaded_image and not st.session_state.messages):
        
        image_to_send = st.session_state.uploaded_image
        
        detected_lang = detect_language(prompt) if prompt else 'en'
        translated_input = translate_text(prompt, 'en') if detected_lang != 'en' else prompt

        user_msg_content = translated_input
        if not user_msg_content and image_to_send:
            user_msg_content = "(Image uploaded)"
            
        user_msg = {"role": "user", "content": user_msg_content}
        if image_to_send:
            user_msg['image'] = image_to_send

        st.session_state.messages.append(user_msg)
        
        response = response_generator(st.session_state.messages, image_to_send)

        with st.chat_message("assistant"):
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.session_state.uploaded_image = None
        st.session_state.uploader_key += 1
        st.rerun()

# ------------------- Routing -------------------
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "signup":
    signup_page()
elif st.session_state.page == "chatbot" and st.session_state.authenticated:
    chatbot_page()