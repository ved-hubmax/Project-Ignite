"""
Jarvis - AI Voice Assistant
Wake word : "Hey Jarvis"  (voice mode)
Text mode : type commands directly — no microphone needed
"""

from __future__ import annotations

import speech_recognition as sr
import pyttsx3
import webbrowser
import subprocess
import os
import sys
import time
import re
import json
from datetime import datetime
from typing import Optional


# ── Input mode ─────────────────────────────────────────────────────────────────
# Set at startup; controls whether speak() uses TTS or print-only,
# and which main loop runs.
INPUT_MODE: str = "voice"   # "voice" | "text"

# ── Text-to-speech engine ──────────────────────────────────────────────────────
engine = pyttsx3.init()
engine.setProperty('rate', 175)
engine.setProperty('volume', 1.0)
voices = engine.getProperty('voices')
for v in voices:
    if 'female' in v.name.lower() or 'zira' in v.name.lower() or 'hazel' in v.name.lower():
        engine.setProperty('voice', v.id)
        break

def speak(text: str):
    """Print Jarvis reply always; also speak aloud in voice mode."""
    print(f"\n[Jarvis] {text}")
    if INPUT_MODE == "voice":
        engine.say(text)
        engine.runAndWait()

# ── URL / app mappings ─────────────────────────────────────────────────────────
SITES = {
    "youtube":       "https://www.youtube.com",
    "gmail":         "https://mail.google.com",
    "whatsapp":      "https://web.whatsapp.com",
    "google":        "https://www.google.com",
    "linkedin":      "https://www.linkedin.com",
    "chatgpt":       "https://chat.openai.com",
    "google meet":   "https://meet.google.com",
    "github":        "https://www.github.com",
    "twitter":       "https://www.twitter.com",
    "instagram":     "https://www.instagram.com",
    "facebook":      "https://www.facebook.com",
    "reddit":        "https://www.reddit.com",
    "netflix":       "https://www.netflix.com",
    "amazon":        "https://www.amazon.in",
    "stackoverflow": "https://stackoverflow.com",
    "spotify" :       "https://www.spotify.com/",
}
# FIX 3: added more sites and made keys more flexible (e.g. "google meet" instead of "meet")
CONTACTS = {
    "pappa":   "+919975150563",
    "jayesh":  "+91 80101 99438",
    "siddhu":  "+919175147710",
    "vedant" : "+919607200919"

}


APPS_WINDOWS = {
    "calculator":    "calc.exe",
    "notepad":       "notepad.exe",
    "file explorer": "explorer.exe",
    "paint":         "mspaint.exe",
    "cmd":           "cmd.exe",
    "task manager":  "taskmgr.exe",
    "word":          "winword.exe",
    "excel":         "excel.exe",
    "powerpoint":    "powerpnt.exe",
    "vlc":           "vlc.exe",
}

APPS_LINUX = {
    "calculator":    "gnome-calculator",
    "notepad":       "gedit",
    "file explorer": "nautilus",
    "terminal":      "gnome-terminal",
    "text editor":   "gedit",
}

# ── Memory ─────────────────────────────────────────────────────────────────────
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

def load_memory() -> dict:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {"last_command": None, "last_urls": [], "history": []}

def save_memory(mem: dict):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)

memory = load_memory()

# Meta-commands that should NOT overwrite last_command
_META_PHRASES = ["repeat last", "do that again", "previous task", "reopen"]

def record_command(cmd: str):
    """FIX 5: skip recording meta/repeat commands so they don't overwrite the real last task."""
    if any(x in cmd for x in _META_PHRASES):
        return
    memory["last_command"] = cmd
    memory["history"].append({"cmd": cmd, "time": datetime.now().isoformat()})
    memory["history"] = memory["history"][-20:]
    save_memory(memory)

# ── Browser helpers ────────────────────────────────────────────────────────────
def open_url(url: str):
    webbrowser.open(url)
    time.sleep(0.4)

def open_site(name: str) -> bool:
    key = name.lower().strip()
    if key in SITES:
        speak(f"Opening {name}")
        open_url(SITES[key])
        memory["last_urls"].append(SITES[key])
        memory["last_urls"] = memory["last_urls"][-10:]   # FIX 7: cap list size
        save_memory(memory)
        return True
    return False

def search_google(query: str):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    speak(f"Searching for {query} on Google")
    open_url(url)

def open_app(name: str) -> bool:
    key = name.lower().strip()
    platform = sys.platform
    try:
        if platform.startswith("win"):
            if key in APPS_WINDOWS:
                speak(f"Opening {name}")
                subprocess.Popen(APPS_WINDOWS[key], shell=True)
                return True
        else:
            if key in APPS_LINUX:
                speak(f"Opening {name}")
                subprocess.Popen(APPS_LINUX[key], shell=True)
                return True
    except Exception as e:
        print(f"[Error] {e}")
    return False

# ── WhatsApp automation ────────────────────────────────────────────────────────
def send_whatsapp(contact: str, message: str):
    # Look up number from CONTACTS dictionary
    number = CONTACTS.get(contact.lower().strip())
    
    if not number:
        speak(f"I don't have a number saved for {contact}. Please add it to the contacts list.")
        return

    # Remove spaces from number for URL
    number = number.replace(" ", "")
    
    speak(f"Opening WhatsApp for {contact}.")
    encoded = message.replace(" ", "%20")
    url = f"https://web.whatsapp.com/send?phone={number}&text={encoded}"
    open_url(url)
    speak("WhatsApp Web opened with your message. Click send.")

# ── Email automation ───────────────────────────────────────────────────────────
def send_email_gmail(to: str, subject: str, body: str):
    speak(f"Opening Gmail to draft an email to {to}")
    b = body.replace(" ", "%20").replace("\n", "%0A")
    s = subject.replace(" ", "%20")
    url = f"https://mail.google.com/mail/?view=cm&to={to}&su={s}&body={b}"
    open_url(url)
    speak("Gmail compose window opened. Please review and send.")

# ── Speech recognition ─────────────────────────────────────────────────────────
recognizer = sr.Recognizer()
recognizer.pause_threshold = 1.0
recognizer.energy_threshold = 300

def listen(timeout=8, phrase_limit=15, prompt="Listening...") -> Optional[str]:  # FIX 2
    print(f"[Jarvis] {prompt}")
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            return None
    try:
        text = recognizer.recognize_google(audio).lower()
        print(f"[You] {text}")
        return text
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        speak("Speech recognition service unavailable.")
        return None

# ── Command parser ─────────────────────────────────────────────────────────────
def extract_sites_from_command(cmd: str) -> list[str]:
    found = []
    for name in sorted(SITES.keys(), key=len, reverse=True):
        if name in cmd:
            found.append(name)
    return found

def extract_apps_from_command(cmd: str) -> list[str]:
    all_apps = {**APPS_WINDOWS, **APPS_LINUX}
    found = []
    for name in sorted(all_apps.keys(), key=len, reverse=True):
        if name in cmd:
            found.append(name)
    return found

def parse_whatsapp(cmd: str):
    if "saying" not in cmd:
        speak("Please include the word 'saying' followed by your message.")
        return None, None

    # Split on "saying" to get message
    parts = cmd.split("saying", 1)
    message = parts[1].strip()

    # Get contact — extract word(s) right before "saying" after "to"
    before_saying = parts[0]
    
    # Find "to" and take everything after it as contact name
    if " to " in before_saying:
        contact = before_saying.split(" to ")[-1].strip()
    else:
        contact = before_saying.strip()

    # Clean up any leftover words
    # Clean whole words only — pad with spaces to avoid partial matches
    for filler in [" send ", " whatsapp ", " message ", " on "]:
     contact = f" {contact} "
     contact = contact.replace(filler, " ").strip()

    print(f"[Debug] Contact: '{contact}' | Message: '{message}'")

    if not contact or not message:
        return None, None

    return contact, message

def parse_email(cmd: str):
    to_match   = re.search(r"(?:to|email)\s+(?:my\s+)?(.+?)(?:\s+with subject|\s+saying|\s+about|\s+with message)", cmd)
    subj_match = re.search(r"(?:subject|titled?)\s+(.+?)(?:\s+(?:and|body|message|saying)\s+)", cmd)
    body_match = re.search(r"(?:message|body|saying)\s+(.+?)$", cmd)
    to      = to_match.group(1).strip()   if to_match   else "recipient"
    subject = subj_match.group(1).strip() if subj_match else "Message from Jarvis"
    body    = body_match.group(1).strip() if body_match else ""
    return to, subject, body

def parse_search(cmd: str) -> Optional[str]:  
    patterns = [
        r"search\s+(?:for\s+)?(.+?)(?:\s+on google)?$",
        r"google\s+(.+?)$",
        r"look up\s+(.+?)$",
        r"find\s+(.+?)\s+on google",
    ]
    for p in patterns:
        m = re.search(p, cmd)
        if m:
            return m.group(1).strip()
    return None

# ── Task executor ──────────────────────────────────────────────────────────────
def execute(cmd: str):
    record_command(cmd)   # FIX 5: now skips meta-commands automatically
    executed = False

    # ── Repeat / reopen ────────────────────────────────────────────────────
    if any(x in cmd for x in _META_PHRASES):
        if "reopen" in cmd or "previous tab" in cmd:
            if memory["last_urls"]:
                speak("Reopening your previous tabs")
                for url in memory["last_urls"][-3:]:
                    open_url(url)
                speak("Done!")
            else:
                speak("No previous tabs found in memory.")
        else:
            last = memory.get("last_command")
            # FIX 4: guard against infinite recursion — last_command cannot be a meta-command
            # because record_command() now skips them, so this branch is safe.
            if last:
                speak("Repeating your last command")
                execute(last)
            else:
                speak("I don't have a previous task in memory.")
        return

    # ── WhatsApp ───────────────────────────────────────────────────────────
    # FIX 1: explicit parentheses fix operator precedence
    if ("whatsapp" in cmd and "send" in cmd) or \
       ("message" in cmd and any(x in cmd for x in ["saying", "that", "tell"])):
        contact, message = parse_whatsapp(cmd)
        if contact and message:
            send_whatsapp(contact, message)
            executed = True
        else:
            speak("Please say: send a WhatsApp message to name saying message")
            return

    # ── Email ──────────────────────────────────────────────────────────────
    if "email" in cmd or "send mail" in cmd:
        to, subject, body = parse_email(cmd)
        send_email_gmail(to, subject, body)
        executed = True

    # ── Multi-site open ────────────────────────────────────────────────────
    sites = extract_sites_from_command(cmd)
    for s in sites:
        open_site(s)
        executed = True

    # ── App open ───────────────────────────────────────────────────────────
    apps = extract_apps_from_command(cmd)
    for a in apps:
        if open_app(a):
            executed = True

    # ── Google search ──────────────────────────────────────────────────────
    if "search" in cmd or "look up" in cmd or (
        "google" in cmd and not any(s in cmd for s in SITES)):
        q = parse_search(cmd)
        if q and not any(s in q for s in SITES):
            search_google(q)
            executed = True

    # ── Greetings / chitchat ───────────────────────────────────────────────
    if any(x in cmd for x in ["hello", "hi jarvis", "how are you" , "hey jarvis"]):
        speak("Hello! I'm doing great. How can I assist you?")
        executed = True

    if any(x in cmd for x in ["what time", "current time"]):
        speak(f"The current time is {datetime.now().strftime('%I:%M %p')}")
        executed = True

    if any(x in cmd for x in ["what date", "today's date", "current date"]):
        speak(f"Today is {datetime.now().strftime('%A, %B %d, %Y')}")
        executed = True

    if any(x in cmd for x in ["stop", "exit", "bye", "shutdown"]):
        speak("Goodbye! Have a productive day.")
        sys.exit(0)

    if not executed:
        speak("I didn't understand that command. Please try again.")

# ── Wake word listener ─────────────────────────────────────────────────────────
WAKE_PHRASES = ["hey jarvis", "jarvis", "ok jarvis"]
GREETINGS    = [
    "Yes, I'm listening.",
    "How can I help you?",
    "Tell me your command.",
    "I'm here. What do you need?",
]
_greeting_idx = 0

def activation_greeting():
    global _greeting_idx
    speak(GREETINGS[_greeting_idx % len(GREETINGS)])
    _greeting_idx += 1

def is_wake_word(text: str) -> bool:
    return any(phrase in text for phrase in WAKE_PHRASES)

# ── Text mode loop ─────────────────────────────────────────────────────────────
def text_loop():
    """Silent mode: user types commands, Jarvis replies in the terminal only."""
    print("\n" + "=" * 55)
    print("  JARVIS — Text Mode  (silent / no microphone)")
    print("  Type a command and press Enter.")
    print("  Type  'switch to voice'  to switch modes.")
    print("  Type  'exit' / 'bye'     to quit.")
    print("=" * 55)
    speak("Jarvis text mode is active. Type your command below.")

    while True:
        try:
            raw = input("\n[You] ").strip()
        except (EOFError, KeyboardInterrupt):
            speak("Goodbye! Have a productive day.")
            sys.exit(0)

        if not raw:
            continue

        cmd = raw.lower()

        if cmd in ("switch to voice", "voice mode"):
            speak("Switching to voice mode. Say Hey Jarvis to activate me.")
            voice_loop()
            return

        execute(cmd)


# ── Voice mode loop ─────────────────────────────────────────────────────────────
def voice_loop():
    """Voice mode: wake-word → listen → execute."""
    print("\n" + "=" * 55)
    print("  JARVIS — Voice Mode")
    print("  Wake word : 'Hey Jarvis'")
    print("  Say       : 'switch to text' to switch modes.")
    print("  Say       : 'stop' / 'exit' to quit.")
    print("=" * 55)
    speak("Jarvis voice mode is active. Say Hey Jarvis to activate me.")

    while True:
        text = listen(timeout=30, phrase_limit=5, prompt="Waiting for wake word...")
        if text is None:
            continue

        # Allow switching to text mode by voice
        if "switch to text" in text or "text mode" in text:
            speak("Switching to text mode.")
            INPUT_MODE_set("text")
            text_loop()
            return

        if not is_wake_word(text):
            continue

        activation_greeting()
        cmd = listen(timeout=10, phrase_limit=20, prompt="Awaiting command...")

        if cmd is None:
            speak("I didn't catch that. Please say Hey Jarvis again.")
            continue

        # Allow mid-session switch to text mode
        if "switch to text" in cmd or "text mode" in cmd:
            speak("Switching to text mode.")
            INPUT_MODE_set("text")
            text_loop()
            return

        execute(cmd)
        speak("Anything else?")


def INPUT_MODE_set(mode: str):
    """Update the global INPUT_MODE."""
    global INPUT_MODE
    INPUT_MODE = mode


# ── Startup mode selector ──────────────────────────────────────────────────────
def choose_mode() -> str:
    """Ask user which input mode to use at startup."""
    print("\n" + "=" * 55)
    print("  JARVIS — AI Assistant")
    print("=" * 55)
    print("\n  Select input mode:")
    print("  [1]  Voice mode  — speak commands (needs microphone)")
    print("  [2]  Text mode   — type commands  (silent / no mic)")
    print()
    while True:
        choice = input("  Enter 1 or 2: ").strip()
        if choice == "1":
            return "voice"
        elif choice == "2":
            return "text"
        else:
            print("  Please enter 1 or 2.")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    global INPUT_MODE
    INPUT_MODE = choose_mode()
    if INPUT_MODE == "text":
        text_loop()
    else:
        voice_loop()


if __name__ == "__main__":
    main()
