from flask import Flask, request, jsonify, render_template
import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv
from gtts import gTTS
import io
import base64

app = Flask(__name__)

# --- Setup (Keep as is) ---
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found!")
genai.configure(api_key=GEMINI_API_KEY)
conversation_history = []

# --- AI Response Function (Keep as is) ---
def get_ai_response(user_query, history):
    # ... (Keep the function that interacts with Gemini) ...
    user_input = user_query
    if not user_input:
        return "Error: Message cannot be empty"
    try:
        history.append({"role": "user", "parts": [user_input]})
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction='''You are my voice assistant. Your name is Deva, call me Sir. Your task is to assist me in my work. You were created by Moksh Bhardwaj to help others with their work.''' # Adjust prompt if needed based on character later
        )
        chat_session = model.start_chat(history=history[:-1])
        response = chat_session.send_message(history[-1])
        model_response = response.text
        history.append({"role": "model", "parts": [model_response]})
        return model_response
    except Exception as e:
        print(f"Error interacting with Gemini API: {e}")
        if history and history[-1]["role"] == "user":
            history.pop()
        return "Sorry, I had trouble connecting to the AI. Please try again."


# --- Personalized Greeting Function (Keep as is) ---
def get_greeting():
    # ... (Keep as is) ...
    now = datetime.datetime.now()
    hour = now.hour
    user_name = "Sir"
    if 5 <= hour < 12: return f"Good morning, {user_name}!"
    elif 12 <= hour < 18: return f"Good afternoon, {user_name}!"
    else: return f"Good evening, {user_name}!"

# --- Flask Routes ---

@app.route('/')
def index():
    greeting = get_greeting()
    return render_template('index.html', greeting=greeting)

@app.route('/chat', methods=['POST'])
def chat():
    """Handles incoming chat messages and returns text + audio with character voice attempt."""
    audio_base64 = None
    try:
        data = request.get_json()
        user_query = data.get('query')
        # <<< Get selected character from frontend >>>
        character = data.get('character', 'deva').lower() # Default to 'deva' if not provided

        if not user_query:
            return jsonify({"error": "No query provided"}), 400

        # --- TODO: Optionally adjust AI prompt based on character ---
        # You could modify the system_instruction in get_ai_response
        # based on the 'character' variable if you want different personalities.

        # Get AI text response
        ai_reply_text = get_ai_response(user_query, conversation_history)

        # --- Generate TTS Audio with Attempted Voice Difference ---
        if not ai_reply_text.startswith("Error:") and not ai_reply_text.startswith("Sorry,"):
            try:
                # --- Voice Selection Logic (Using gTTS tld as placeholder) ---
                # !! IMPORTANT !!: gTTS offers limited voice control.
                # For distinct male/female voices, integrate a cloud TTS service
                # (e.g., Google Cloud TTS, AWS Polly) and select specific voice IDs.
                tts_lang = 'en'
                if character == 'devi':
                    # Attempt to use a potentially female-sounding accent (e.g., Australian)
                    tts_tld = 'com.au'
                    print(f"Generating TTS for Devi (using tld={tts_tld})")
                else: # Default to Deva
                    # Attempt to use a potentially male-sounding accent (e.g., Indian/US)
                    tts_tld = 'co.in' # or 'com' for US
                    print(f"Generating TTS for Deva (using tld={tts_tld})")

                tts = gTTS(text=ai_reply_text, lang=tts_lang, tld=tts_tld, slow=False)

                # --- Generate and encode audio (Keep as is) ---
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                audio_fp.seek(0)
                audio_base64 = base64.b64encode(audio_fp.read()).decode('utf-8')
                audio_fp.close()

            except Exception as tts_error:
                print(f"Error generating TTS: {tts_error}")
                # Proceed without audio if TTS fails

        # Return response
        return jsonify({
            "response": ai_reply_text,
            "audio_content": audio_base64
        })

    except Exception as e:
        print(f"Error processing chat route: {e}")
        error_message = "Sorry, an internal error occurred."
        return jsonify({"response": error_message, "audio_content": None}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) # Use host='0.0.0.0' if running in Docker/VM
