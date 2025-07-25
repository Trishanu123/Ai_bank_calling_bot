

# 📞 AI-Powered Loan Recovery Bot using Flask, Twilio, and Whisper

This project is an **AI-driven voice bot** developed for the **Loan Recovery Department of Axis Bank**. It automates outbound calls to customers, asks a series of loan-related questions using natural speech, and uses Whisper (for transcription) and an LLM (OpenChat) for intelligent response flow. The interaction is stored and analyzed for compliance, and data is logged into a CSV for further review.

---

## 🌟 Features

* 📲 **Twilio Integration** for voice call handling.
* 🧠 **LLM-powered conversation flow** using OpenChat.
* 🗣️ **Real-time speech-to-text** using OpenAI’s Whisper.
* 📁 **Auto-saves user responses** to a CSV file.
* 🎤 **Voice output using Amazon Polly (Aditi)** for natural-sounding Hindi-English voice.
* 🧾 **Loan recovery logic flow** embedded in assistant.
* ✅ Fully automated — the system makes the call, runs the flow, and logs the results.

---

## 🧠 Tech Stack

| Component            | Tool/Library                        |
| -------------------- | ----------------------------------- |
| Backend Server       | Flask (Python)                      |
| Call API             | Twilio Voice API                    |
| Speech-to-Text       | OpenAI Whisper                      |
| LLM Chat Flow        | OpenChat API (local)                |
| TTS Voice            | Amazon Polly (via Twilio)           |
| Recording Conversion | ffmpeg                              |
| Secrets              | Python `dotenv`                     |
| Data Storage         | CSV File (`loan_recovery_data.csv`) |

---

## 📁 Project Structure

```
.
├── app.py                        # Main Flask app
├── .env                          # Environment secrets (Twilio creds etc.)
├── loan_recovery_data.csv        # CSV storing all call responses
├── input.mp3 / input.wav         # Temporary recording files
├── README.md                     # You're here!
```

---

## 🧰 Prerequisites

* Python 3.8+
* Ngrok (for exposing localhost to Twilio)
* Twilio account with a verified number
* ffmpeg installed on your system
* Whisper and torch installed via pip

---

## ⚙️ Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/ai-loan-recovery-bot.git
cd ai-loan-recovery-bot

# Install dependencies
pip install -r requirements.txt

# Install ffmpeg (if not already)
sudo apt install ffmpeg         # For Linux
brew install ffmpeg             # For macOS

# Set environment variables
cp .env.example .env
# Edit .env and fill in your Twilio credentials and phone numbers
```

### `.env` Sample

```env
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1XXX...
TARGET_PHONE_NUMBER=+91XXXX...
```

---

## 🧪 Running the App

### Step 1: Start Flask Server

```bash
python app.py
```

### Step 2: Start Ngrok (in separate terminal)

```bash
ngrok http 5500
```

Update the `ngrok_url` in `make_initial_call()` with the new HTTPS URL generated by Ngrok.

### Step 3: Twilio Call Begins Automatically

Once the server runs, it automatically makes a call using Twilio to the number provided in `.env`.

---

## 🔁 Call Flow Breakdown

1. **/voice**

   * Entry point for Twilio call
   * Starts intro message and redirects to `/ask_next`

2. **/ask\_next**

   * Calls `ask_question()` to ask a predefined question from the bot

3. **/process**

   * Downloads recorded audio
   * Converts `.mp3` → `.wav`
   * Uses Whisper to transcribe speech
   * Uses OpenChat LLM to determine how to respond or re-ask

4. **/save**

   * Callback from Twilio when recording completes (no logic here)

---

## 📒 Question Flow Logic

The bot asks **4 questions**:

1. Name
2. Is this your linked loan number?
3. What was your loan amount?
4. Did you repay the loan on time?

Based on responses:

* If a user says *“No”* to timely repayment → triggers a warning message
* If irrelevant input → repeats same question
* If complete → thanks and ends call

---

## 💾 Data Storage

All responses are saved in a file called `loan_recovery_data.csv` with the following columns:

| Timestamp | Call SID | Name | Linked Number | Loan Amount | Repaid On Time |
| --------- | -------- | ---- | ------------- | ----------- | -------------- |

---

## 🗣️ Voice and Transcription

* Bot uses **Amazon Polly's Aditi voice** (Hindi-English female).
* Audio is recorded and transcribed using **Whisper (base model)**.
* The bot understands and responds intelligently using **OpenChat LLM** via a locally running instance.

---

## 📦 Dependencies

You can create a `requirements.txt` file like this:

```txt
Flask
requests
twilio
whisper
python-dotenv
openai-whisper
```

And install with:

```bash
pip install -r requirements.txt
```

---

## 🛑 Limitations

* LLM (`/process`) assumes a local OpenChat instance at `http://localhost:11434/api/chat`.
* No database is used; CSV is the only log.
* Doesn't support incoming calls (only outbound).

---

## 🚀 Deployment Ideas

* ☁️ Deploy on a server or cloud VM
* 🔄 Schedule calls in batches
* 📊 Export CSV to CRM or database
* 🌐 Host LLM on cloud or container for scalability

---

## 🙋 FAQ

**Q: What if the user gives incomplete or unrelated responses?**
A: The LLM detects relevance using keywords and context. If irrelevant, it repeats the question.

**Q: Is the call two-way voice or just keypad-based?**
A: It is two-way voice — the system uses STT (Whisper) and TTS (Polly).

**Q: Can this work without Ngrok?**
A: Yes, but you’ll need a public URL (via cloud or domain).

---

## 🙌 Contributing

Feel free to fork, improve, or adapt for other use-cases like:

* Appointment reminders
* Debt collection
* Automated surveys
* Customer support bots

Pull requests welcome!

---

## 📄 License

MIT License – Free to use with attribution.

---