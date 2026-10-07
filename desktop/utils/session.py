"""Remember login for 1 day: stores session tokens locally, auto-restores if fresh."""
import json
import os
import time

APP_DIR = os.path.join(os.path.expanduser("~"), ".invoice_tracker")
SESSION_FILE = os.path.join(APP_DIR, "session.json")
MAX_AGE = 24 * 3600  # 1 day


def save_session(access_token, refresh_token, email=""):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump({"access_token": access_token, "refresh_token": refresh_token,
                       "email": email, "saved_at": int(time.time())}, f)
    except OSError:
        pass


def load_session():
    try:
        with open(SESSION_FILE, encoding="utf-8") as f:
            d = json.load(f)
        if int(time.time()) - int(d.get("saved_at", 0)) > MAX_AGE:
            clear_session()
            return None
        if not d.get("access_token") or not d.get("refresh_token"):
            return None
        return d
    except (OSError, ValueError, KeyError):
        return None


def clear_session():
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except OSError:
        pass
