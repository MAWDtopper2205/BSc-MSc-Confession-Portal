# BSc-MSc Confession Portal

A simple MAWD project using Python, FastAPI, SQLite3, Jinja2, HTML and CSS.

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
- Their private one-time invitation code from the separate `invitation_codes.txt` file (provided with the project download)
- A password they create during registration

After registering once, they log in using their student ID and password. The invitation code cannot be reused. Do not upload `invitation_codes.txt` to a public GitHub repository; share each code privately with its matching student.

## Main features

- Login required to access the main portal
- Ten student profiles
- Ranking graph with circles connected by a line
- Click a profile to open its confession page
- Anonymous confession posting
- Like/unlike confessions
- Live ranking based on total likes received
- Password hashing with `hashlib.pbkdf2_hmac`
- Signed JWT stored in an HttpOnly cookie

The profile circles show initials as placeholders because no profile photos were supplied. Add photos only after receiving permission.

The graph ranks profiles by likes received on confessions. It does not measure intelligence or ability. Keep posts lighthearted and respectful. Do not post private information, threats, or humiliating content. Use profile photos only with the person's permission.

## Existing database

If you already have a `batch_exposed.db` from the earlier version, keep a backup before running this updated version. The app adds the new student ID and invitation fields automatically and updates the ten placeholder student records.

## Before public deployment

- Set a strong random `JWT_SECRET` environment variable.
- Set the cookie `secure=True` when using HTTPS.
- Add CSRF protection, rate limiting and moderation before allowing public access.
- Never commit invitation codes or real student passwords to GitHub.
