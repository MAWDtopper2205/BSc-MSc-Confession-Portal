# BSc-MSc Confession Portal

An anonymous confession platform built for the BSc-MSc AI & DS batch. Students can share anonymous confessions, interact with posts, and view a live ranking graph based on the likes received by each student's confessions.

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** SQLite3
- **Templating:** Jinja2
- **Frontend:** HTML, CSS, JavaScript
- **Authentication:** JWT (JSON Web Tokens)
- **Password Security:** `hashlib.pbkdf2_hmac`

## Features

- **Student Authentication:** Only the 10 pre-approved students can register and access the portal.
- **One-Time Registration:** Registration requires a valid student ID and a private invitation code.
- **Anonymous Confessions:** Share confessions without displaying the author's identity.
- **Individual Student Pages:** Click on a student's profile to view and post confessions.
- **Like & Unlike:** Interact with confessions using the like/unlike feature.
- **Live Ranking Graph:** Displays all 10 students in a ranking graph based on the total likes received on their confessions.

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

## Security

- Passwords are hashed using `hashlib.pbkdf2_hmac`.
- Authentication uses signed JWT tokens.
- JWT tokens are stored in HttpOnly cookies.
- Invitation codes are stored as SHA-256 hashes and can only be used once.

## Project Structure

```text
BSc_MSc_Confession_Portal/
│
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── static/
│   ├── style.css
│   └── avatars/
│
└── templates/
    ├── auth.html
    ├── base.html
    ├── index.html
    └── student.html
```

---

**Built as a BSc-MSc AI & DS batch project.**
