from flask import Flask, request, jsonify, render_template
import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv
from gtts import gTTS
import io
import base64

app = Flask(__name__)

# --- Setup ---
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found!")
genai.configure(api_key=GEMINI_API_KEY)

# !! IMPORTANT CAVEAT !!
# Using a global variable for history means the conversation is shared across
# ALL users and sessions accessing this Flask app simultaneously.
# For a real application, you'd typically manage history per user session.
conversation_history = []

# --- AI Response Function (Modified) ---
def get_ai_response(user_query, history, character='deva'): # Added character parameter
    """Gets response from Gemini, adjusting system prompt based on character."""
    user_input = user_query
    if not user_input:
        return "Error: Message cannot be empty"

    # --- Dynamically set system instruction ---
    if character == 'devi':
        system_instruction = '''You are my voice assistant. Your name is Devi, call me Sir. Your task is to assist me in my work. You were created by Moksh Bhardwaj to help others with their work.'''
    else: # Default to Deva
        system_instruction = '''You are my voice assistant. Your name is Deva, call me Sir. Your task is to assist me in my work. You were created by Moksh Bhardwaj to help others with their work.'''

    try:
        # Append user message *before* starting chat for context
        history.append({"role": "user", "parts": [user_input]})

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction # Use the dynamic instruction
        )
        # Pass the history *up to the last user message* to start_chat
        chat_session = model.start_chat(history=history[:-1])
        response = chat_session.send_message(history[-1]) # Send the latest user message
        model_response = response.text

        # Append model response to history
        history.append({"role": "model", "parts": [model_response]})

        return model_response
    except Exception as e:
        print(f"Error interacting with Gemini API: {e}")
        # Remove the user message if the API call failed
        if history and history[-1]["role"] == "user":
            history.pop()
        return "Sorry, I had trouble connecting to the AI. Please try again."


# --- Personalized Greeting Function (Keep as is) ---
def get_greeting():
    now = datetime.datetime.now()
    hour = now.hour
    user_name = "Sir" # Or potentially get from user session later
    if 5 <= hour < 12: return f"Good morning, {user_name}!"
    elif 12 <= hour < 18: return f"Good afternoon, {user_name}!"
    else: return f"Good evening, {user_name}!"

# --- Flask Routes ---

@app.route('/')
def index():
    # Greeting is generic, doesn't depend on character selection yet
    greeting = get_greeting()
    # Clear history when the root page is loaded (simple reset for this example)
    # Note: This clears for *everyone* if multiple people use it.
    global conversation_history
    conversation_history = []
    print("Conversation history cleared on page load.")
    return render_template('index.html', greeting=greeting)

@app.route('/chat', methods=['POST'])
def chat():
    """Handles incoming chat messages and returns text + audio with character voice attempt."""
    audio_base64 = None
    try:
        data = request.get_json()
        if not data:
             return jsonify({"error": "Invalid JSON payload"}), 400

        user_query = data.get('query')
        # Get selected character from frontend, default to 'deva'
        character = data.get('character', 'deva').lower()
        # Optional: Get settings from frontend if needed for TTS later
        # settings = data.get('settings', {})
        # lang_code = settings.get('language', 'en-IN') # Example

        if not user_query:
            return jsonify({"error": "No query provided"}), 400

        # Get AI text response using the selected character
        # Pass the *current* conversation history
        ai_reply_text = get_ai_response(user_query, conversation_history, character)

        # --- Generate TTS Audio with Attempted Voice Difference ---
        if not ai_reply_text.startswith("Error:") and not ai_reply_text.startswith("Sorry,"):
            try:
                # --- Voice Selection Logic (Using gTTS tld as placeholder) ---
                # !! IMPORTANT !!: gTTS offers limited voice control via tld accents.
                # For distinct male/female voices, integrate a cloud TTS service
                # (e.g., Google Cloud TTS, AWS Polly, ElevenLabs) and select specific voice IDs.
                tts_lang = 'en' # Base language
                # You could potentially use the language setting from the frontend here:
                # tts_lang = lang_code.split('-')[0] if lang_code else 'en'

                if character == 'devi':
                    # Attempt to use a potentially female-sounding accent (e.g., Australian, UK)
                    tts_tld = 'com.au' # or 'co.uk'
                    print(f"Generating TTS for Devi (using lang={tts_lang}, tld={tts_tld})")
                else: # Default to Deva
                    # Attempt to use a potentially male-sounding accent (e.g., Indian, US)
                    tts_tld = 'co.in' # or 'com' for US
                    print(f"Generating TTS for Deva (using lang={tts_lang}, tld={tts_tld})")

                tts = gTTS(text=ai_reply_text, lang=tts_lang, tld=tts_tld, slow=False)

                # --- Generate and encode audio ---
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                audio_fp.seek(0)
                audio_base64 = base64.b64encode(audio_fp.read()).decode('utf-8')
                audio_fp.close()
                print(f"TTS generated successfully for {character}.")

            except Exception as tts_error:
                print(f"Error generating TTS: {tts_error}")
                # Proceed without audio if TTS fails, client will handle null audio_content

        # Return response including the AI text and potentially the audio
        return jsonify({
            "response": ai_reply_text,
            "audio_content": audio_base64 # Will be null if TTS failed or wasn't attempted
        })

    except Exception as e:
        print(f"Error processing chat route: {e}")
        # Log the full traceback for debugging if needed
        import traceback
        traceback.print_exc()
        error_message = "Sorry, an internal server error occurred."
        # Avoid sending potentially sensitive error details to the client
        return jsonify({"response": error_message, "audio_content": None}), 500

# --- Optional: Add a route to clear history explicitly ---
@app.route('/clear_history', methods=['POST'])
def clear_history_route():
    global conversation_history
    conversation_history = []
    print("Conversation history cleared via API call.")
    return jsonify({"message": "History cleared"}), 200


if __name__ == '__main__':
    # Use host='0.0.0.0' to make accessible on your network if needed
    app.run(debug=True, port=5000)
