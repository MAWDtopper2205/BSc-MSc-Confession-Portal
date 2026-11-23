# BSc-MSc Confession Portal

Anonymous confession portal with live student ranking built using Python, FastAPI, SQLite3, Jinja2, HTML and CSS.

## Run on Windows

Open this project folder in VS Code and run these commands in the terminal:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`.

## Student registration

The 10 approved student IDs and names are preloaded automatically when the app starts.

Each student must use:
- Their own student ID
- Their private one-time invitation code
- A password they create during registration

After registering once, they log in using their student ID and password. The invitation code cannot be reused.

## Main features

- Login required to access the main portal
- Click a profile to open its confession page
- Anonymous confession posting
- Like/unlike confessions
- Live ranking based on total likes received
- Password hashing with `hashlib.pbkdf2_hmac`
- Signed JWT stored in an HttpOnly cookie

The graph ranks profiles by likes received on confessions. It does not measure intelligence or ability. Don't Keep posts lighthearted and respectful. Please post private information, threats, or humiliating content.
