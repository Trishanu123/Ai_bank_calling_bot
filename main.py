from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import whisper
import requests
import subprocess
import time
import warnings
import threading
import json
import re
import csv
import os
from datetime import datetime
from dotenv import load_dotenv  # ✅ NEW

# ✅ Load .env variables
load_dotenv()

app = Flask(__name__)

# ✅ Twilio credentials from environment
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
target_number = os.getenv('TARGET_PHONE_NUMBER')

client = Client(account_sid, auth_token)

# rest of your code continues exactly the same...

# Whisper model
model = whisper.load_model("base")
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

# Global conversation state
conversation_state = {}

# CSV setup
CSV_FILE = "loan_recovery_data.csv"
if not os.path.isfile(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            "timestamp", "call_sid", 
            "name", "linked_number", "loan_amount", "repaid_on_time"
        ])

# Questions
questions = [
    "To get started, may I know your full name please?",
    "Just to confirm — is this the phone number linked to your loan account?",
    "Could you let me know the total loan amount you had taken?",
    "Have you been able to repay the loan on time?"
]

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    call_sid = request.values.get("CallSid", "")
    conversation_state[call_sid] = {
        "step": 0,
        "answers": {},
        "warned": False,
        "chat_history": [
            {
                "role": "system",
                "content": (
                    "You are an AI assistant from Axis Bank's Loan Recovery Department, calling to confirm important loan details. "
                    "This call is being recorded. Keep the tone friendly, natural, and professional.\n\n"
                    "Conversation flow:\n"
                    "- Begin with a warm introduction and mention the call is recorded.\n"
                    "- Ask user's name. If name is given, proceed.\n"
                    "- Confirm if this number is linked to their loan. If 'no', apologize and end the call.\n"
                    "- Then ask loan amount. If unclear, re-ask politely.\n"
                    "- Ask if they have repaid the loan on time.\n"
                    "- If they say 'no', warn about consequences.\n"
                    "- If all done, thank them and ask them to hang up.\n"
                    "- Never ask unrelated questions or improvise."
                )
            },
            {
                "role": "assistant",
                "content": (
                    "Hi there! This is an automated call from Axis Bank's Loan Recovery Department. "
                    "We just need to verify a few quick details. This call is being recorded for quality and security purposes."
                )
            }
        ]
    }

    vr = VoiceResponse()
    vr.say(conversation_state[call_sid]["chat_history"][1]["content"], voice="Polly.Aditi")
    vr.redirect("/ask_next")
    return Response(str(vr), mimetype="text/xml")

@app.route("/ask_next", methods=['GET', 'POST'])
def ask_next():
    call_sid = request.values.get("CallSid", "")
    return ask_question(call_sid)

@app.route("/save", methods=['POST'])
def save_recording():
    return Response("Recording saved", status=200)

@app.route("/process", methods=['POST'])
def process():
    call_sid = request.form.get('CallSid', '')
    recording_url = request.form['RecordingUrl'] + '.mp3'
    print(f"🔗 Downloading: {recording_url}")
    time.sleep(2)

    r = requests.get(recording_url, auth=(account_sid, auth_token))
    if r.status_code != 200 or len(r.content) < 1000:
        print("❌ Recording download failed or too short")
        return Response("Recording failed", status=400)

    with open("input.mp3", "wb") as f:
        f.write(r.content)
    subprocess.run(["ffmpeg", "-y", "-i", "input.mp3", "-ar", "16000", "-ac", "1", "input.wav"])

    print("🔍 Transcribing...")
    result = model.transcribe("input.wav")
    user_response = result["text"].strip()
    print("🗣️ You said:", user_response)

    state = conversation_state.get(call_sid)
    if not state:
        return Response("Invalid call state", status=400)

    step = state["step"]
    current_question = questions[step]

    state["chat_history"].append({"role": "user", "content": user_response})

    system_instruction = {
        "role": "system",
        "content": (
            f"You are an AI assistant from Axis Bank. You asked: '{current_question}'. "
            f"The user replied: '{user_response}'.\n\n"
            "Rules:\n"
            "- If the response is off-topic, vague, or evasive, clarify politely and repeat the same question.\n"
            "- If the user asks if this is spam or shows concern, reassure them politely and explain the importance.\n"
            "- If they refuse to answer, explain that it’s essential to proceed and ask again.\n"
            "- Only move to the next question if the answer clearly relates to the current question.\n"
            "- Keep responses short, polite, and professional."
        )
    }

    messages = state["chat_history"] + [system_instruction]

    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": "openchat", "messages": messages},
            stream=True
        )
        assistant_reply = ""
        for line in response.iter_lines(decode_unicode=True):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                assistant_reply += data.get("message", {}).get("content", "")
            except json.JSONDecodeError:
                continue
    except Exception as e:
        print("⚠️ LLM Error:", e)
        assistant_reply = "Sorry, I didn’t quite get that. Could you please repeat?"

    assistant_reply = assistant_reply.strip() or "Sorry, could you please repeat?"
    print(f"🤖 AI says: {assistant_reply}")
    state["chat_history"].append({"role": "assistant", "content": assistant_reply})

    relevance_keywords = ["name", "loan", "rupees", "amount", "yes", "no", "repaid", "number", "lakhs", "linked"]
    valid = any(word in user_response.lower() for word in relevance_keywords)

    if valid:
        key = f"answer_{step + 1}"
        state["answers"][key] = user_response
        if step == 3 and any(x in user_response.lower() for x in ["no", "not", "haven't", "didn't"]):
            state["warned"] = True
        state["step"] += 1
    else:
        print("⚠️ Off-topic or unclear. Re-asking same question.")
        return ask_question(call_sid, fallback=assistant_reply)

    return ask_question(call_sid)

def ask_question(call_sid, fallback=None):
    state = conversation_state.get(call_sid)
    step = state["step"]
    vr = VoiceResponse()

    if step == len(questions) and state["warned"]:
        warning = (
            "Thank you for your honesty. Please be aware that not repaying your loan on time may result in legal action "
            "and negatively affect your credit score."
        )
        state["chat_history"].append({"role": "assistant", "content": warning})
        vr.say(warning, voice="Polly.Aditi")
        state["step"] += 1
        return Response(str(vr), mimetype="text/xml")

    if step >= len(questions) + (1 if state["warned"] else 0):
        closing = (
            "Thanks for confirming the details. That’s all we needed. "
            "You may now hang up the call. Have a wonderful day!"
        )
        state["chat_history"].append({"role": "assistant", "content": closing})
        save_answers_to_csv(call_sid)
        print(f"✅ Final extracted answers: {json.dumps(state['answers'], indent=2)}")
        vr.say(closing, voice="Polly.Aditi")
        return Response(str(vr), mimetype="text/xml")

    question = questions[step]
    state["chat_history"].append({"role": "assistant", "content": question})

    prompt = fallback if fallback else question
    prompt = re.sub(r'^[^a-zA-Z0-9]+', '', prompt)
    print(f"🤖 Bot asks: {prompt}")
    vr.say(prompt, voice="Polly.Aditi")
    vr.record(
        max_length=6,
        play_beep=True,
        action="/process",
        recording_status_callback="/save"
    )
    return Response(str(vr), mimetype="text/xml")

def save_answers_to_csv(call_sid):
    state = conversation_state.get(call_sid)
    if not state:
        return
    answers = state.get("answers", {})
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [
        timestamp,
        call_sid,
        answers.get("answer_1", ""),
        answers.get("answer_2", ""),
        answers.get("answer_3", ""),
        answers.get("answer_4", "")
    ]
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(row)
    print(f"📁 Answers saved to CSV for Call SID: {call_sid}")

def make_initial_call():
    time.sleep(2)
    ngrok_url = 'https://c4aa-49-206-46-208.ngrok-free.app'
    call = client.calls.create(
        to=target_number,
        from_=twilio_number,
        url=f'{ngrok_url}/voice'
    )
    print(f"📞 Call initiated! SID: {call.sid}")

if __name__ == "__main__":
    threading.Thread(target=make_initial_call).start()
    app.run(debug=True, port=5500)
