# backend.py

import google.generativeai as genai
from PIL import Image
import os;
# Configure API key
genai.configure(api_key="Your_Api_Key")  # ❗ Replace with your actual API key

# Model config
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Load model
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Main response generator
def GenerateResponse(input_text=None, image=None):
    parts = []
    if input_text:
        parts.append(input_text)
    if image and isinstance(image, Image.Image):  # Ensure it's a PIL Image
        parts.append(image)
    
    # Handle case with no text or image, to prevent API error
    if not parts:
        return "Please provide a text or an image to start the conversation."

    response = model.generate_content(parts)
    return response.text