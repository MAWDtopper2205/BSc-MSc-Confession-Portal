import os
import sqlite3
import hashlib
import hmac
import secrets
import base64
import json
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

DB = os.getenv("DATABASE_PATH", "batch_exposed.db")
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-before-submission")
TOKEN_SECONDS = 60 * 60 * 24 * 3

# Only invitation-code hashes are stored in the application.
# Give each student their matching code privately from invitation_codes.txt.
STUDENT_SEED = [
    ("25IMAI001", "ZAID BAGWAN", "ZB"),
    ("25IMAI003", "DEVANSH SHARMA", "DS"),
    ("25IMAI004", "TANISHQ KURI", "TK"),
    ("25IMAI005", "KARTIKAY GARG", "KG"),
    ("25IMAI006", "NEHAL YADAV", "NY"),
    ("25IMAI007", "RISHABH BHAWSINGKA", "RB"),
    ("25IMAI011", "PRIYAL AGARWAL", "PA"),
    ("25IMDS001", "AKSHATA CHOUDHARY", "AC"),
    ("25IMDS002", "ARYAN KUMAWAT", "AK"),
    ("25IMDS003", "PURUJIT SHARMA", "PS"),
]

# Replaced at build time with SHA-256 hashes for the one-time invitation codes.
INVITE_HASHES = {
    "25IMAI001": "2074e3c8c49fd5b4414cddf902fad7152daf1bda793eeccca396b016a749b3e3",
    "25IMAI003": "2261d6f559399dc05759927a89eb4f32ac7fc8dffc2e020ab4c7da0615683c31",
    "25IMAI004": "d9e9d49624258b48b3fc88b6f63e7bba68b533214fdfda49224a36be9854ad95",
    "25IMAI005": "da6dae5b57527f86befa4e6f59b53e7dd3b3c5606c3250df8547c3b79dae3747",
    "25IMAI006": "ec57ed72af990d908fd287841f4e7db8d8075d9233d30b5ba1bcd0e76adc69ea",
    "25IMAI007": "1c2af787fbb287a97d59ff3185aa104aecb453001d4012a4fcdb94a7a2063c2f",
    "25IMAI011": "1e1c527eb7142e1a04ad7623d6ca0014980b7c13bc211ec59d4abc972aea8ead",
    "25IMDS001": "fc4165e277f44773de397e8dcd7a3fa2bf093ec18808af83846b9c7fd930dd2c",
    "25IMDS002": "a68f5c3c56564fda74a7be4b0a49458af053c6a8c27e8fde9821f848046ba62d",
    "25IMDS003": "4a2f2068bd3d7659e9ceb1309ba8be697b141e79115a4a685e30930a43f628d9",
}

app = FastAPI(title="BSc-MSc Confession Portal")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def add_column_if_missing(con, table, column, definition):
    columns = [row["name"] for row in con.execute(f"PRAGMA table_info({table})")]
    if column not in columns:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            initials TEXT NOT NULL,
            avatar_url TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS confessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL CHECK(length(message) <= 280),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            confession_id INTEGER NOT NULL REFERENCES confessions(id) ON DELETE CASCADE,
            UNIQUE(user_id, confession_id)
        );
        """)

        # Add the new registration fields to an existing database safely.
        add_column_if_missing(con, "students", "student_code", "TEXT")
        add_column_if_missing(con, "students", "invite_hash", "TEXT")
        add_column_if_missing(con, "students", "invite_used", "INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(con, "users", "student_code", "TEXT")

        # Convert the ten old placeholder records into the real batch directory.
        existing_count = con.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        for index, (student_code, name, initials) in enumerate(STUDENT_SEED, start=1):
            invite_hash = INVITE_HASHES[student_code]
            if index <= existing_count:
                con.execute("""
                    UPDATE students
                    SET name=?, initials=?, student_code=?,
                        invite_hash=COALESCE(invite_hash, ?)
                    WHERE id=?
                """, (name, initials, student_code, invite_hash, index))
            else:
                con.execute("""
                    INSERT INTO students(name, initials, student_code, invite_hash, invite_used)
                    VALUES(?,?,?,?,0)
                """, (name, initials, student_code, invite_hash))

        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_students_student_code ON students(student_code)")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_student_code ON users(student_code)")


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return base64.b64encode(salt + digest).decode()


def verify_password(password: str, saved: str) -> bool:
    try:
        raw = base64.b64decode(saved)
        salt, expected = raw[:16], raw[16:]
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def create_jwt(user_id: int) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64url(json.dumps({"sub": str(user_id), "exp": int(time.time()) + TOKEN_SECONDS}).encode())
    unsigned = f"{header}.{payload}"
    signature = b64url(hmac.new(JWT_SECRET.encode(), unsigned.encode(), hashlib.sha256).digest())
    return f"{unsigned}.{signature}"


def decode_jwt(token: str) -> Optional[int]:
    try:
        header, payload, signature = token.split(".")
        unsigned = f"{header}.{payload}"
        expected = b64url(hmac.new(JWT_SECRET.encode(), unsigned.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(data["exp"]) < int(time.time()):
            return None
        return int(data["sub"])
    except Exception:
        return None


def get_user(request: Request):
    token = request.cookies.get("access_token")
    user_id = decode_jwt(token) if token else None
    if not user_id:
        return None
    with connect() as con:
        return con.execute(
            "SELECT id, name, student_code FROM users WHERE id=?", (user_id,)
        ).fetchone()


def render(request, template, **values):
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={"request": request, "user": get_user(request), **values},
    )


def login_cookie(user_id: int):
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "access_token",
        create_jwt(user_id),
        httponly=True,
        samesite="lax",
        max_age=TOKEN_SECONDS,
        # Set secure=True when deployed over HTTPS.
        secure=False,
    )
    return response


@app.on_event("startup")
def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    with connect() as con:
        students = con.execute("""
            SELECT s.id, s.name, s.initials, s.avatar_url,
                   COALESCE((
                       SELECT SUM((SELECT COUNT(*) FROM likes l
                                   WHERE l.confession_id=c.id))
                       FROM confessions c WHERE c.student_id=s.id
                   ), 0) AS score
            FROM students s
            ORDER BY s.id ASC
        """).fetchall()

    # Keep the x-axis in fixed batch roster order; y-axis shows live ranking.
    ranked_students = sorted(
        students,
        key=lambda student: (-student["score"], student["name"].casefold())
    )
    rank_by_id = {
        student["id"]: rank
        for rank, student in enumerate(ranked_students, start=1)
    }

    chart_students = []
    for column, student in enumerate(students):
        rank = rank_by_id[student["id"]]
        x = 50 + column * 100
        y = 40 + (rank - 1) * 52
        chart_students.append({
            "id": student["id"],
            "name": student["name"],
            "initials": student["initials"],
            "avatar_url": student["avatar_url"],
            "score": student["score"],
            "rank": rank,
            "x": x,
            "y": y,
        })
    line_points = " ".join(f'{s["x"]},{s["y"]}' for s in chart_students)
    return render(
        request,
        "index.html",
        chart_students=chart_students,
        line_points=line_points,
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    if get_user(request):
        return RedirectResponse("/", status_code=303)
    return render(request, "auth.html", mode="register")


@app.post("/register")
def register(
    student_code: str = Form(...),
    invite_code: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    student_code = student_code.strip().upper()
    invite_code = invite_code.strip().upper()

    if len(password) < 8:
        return RedirectResponse("/register?error=Password must be at least 8 characters", status_code=303)
    if password != confirm_password:
        return RedirectResponse("/register?error=Passwords do not match", status_code=303)

    supplied_hash = hashlib.sha256(invite_code.encode()).hexdigest()
    try:
        with connect() as con:
            student = con.execute(
                "SELECT id, name FROM students WHERE student_code=? AND invite_hash=? AND invite_used=0",
                (student_code, supplied_hash),
            ).fetchone()
            if not student:
                return RedirectResponse(
                    "/register?error=Invalid ID, invitation code, or this ID is already registered",
                    status_code=303,
                )

            # Claim the invitation once. The transaction rolls back if account creation fails.
            changed = con.execute(
                "UPDATE students SET invite_used=1 WHERE id=? AND invite_used=0",
                (student["id"],),
            ).rowcount
            if changed != 1:
                return RedirectResponse("/register?error=This student ID has already been registered", status_code=303)

            email_placeholder = student_code.lower() + "@batch.local"
            con.execute(
                "INSERT INTO users(name,email,password_hash,student_code) VALUES(?,?,?,?)",
                (student["name"], email_placeholder, password_hash(password), student_code),
            )
            user_id = con.execute(
                "SELECT id FROM users WHERE student_code=?", (student_code,)
            ).fetchone()["id"]
    except sqlite3.IntegrityError:
        return RedirectResponse("/register?error=This student ID already has an account", status_code=303)

    return login_cookie(user_id)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_user(request):
        return RedirectResponse("/", status_code=303)
    return render(request, "auth.html", mode="login")


@app.post("/login")
def login(student_code: str = Form(...), password: str = Form(...)):
    student_code = student_code.strip().upper()
    with connect() as con:
        user = con.execute(
            "SELECT * FROM users WHERE student_code=?", (student_code,)
        ).fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        return RedirectResponse("/login?error=Invalid student ID or password", status_code=303)
    return login_cookie(user["id"])


@app.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@app.get("/student/{student_id}", response_class=HTMLResponse)
def student_page(student_id: int, request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    with connect() as con:
        student = con.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        if not student:
            raise HTTPException(404, "Student not found")
        confessions = con.execute("""
            SELECT c.id, c.message, c.created_at,
                   (SELECT COUNT(*) FROM likes l WHERE l.confession_id=c.id) AS likes,
                   EXISTS(SELECT 1 FROM likes l
                          WHERE l.confession_id=c.id AND l.user_id=?) AS liked
            FROM confessions c
            WHERE c.student_id=?
            ORDER BY c.created_at DESC
        """, (user["id"], student_id)).fetchall()

    return render(request, "student.html", student=student, confessions=confessions)


@app.post("/student/{student_id}/confess")
def confess(student_id: int, request: Request, message: str = Form(...)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    message = message.strip()
    if len(message) < 3 or len(message) > 280:
        return RedirectResponse(
            f"/student/{student_id}?error=Write between 3 and 280 characters",
            status_code=303,
        )

    with connect() as con:
        if not con.execute("SELECT id FROM students WHERE id=?", (student_id,)).fetchone():
            raise HTTPException(404, "Student not found")
        con.execute(
            "INSERT INTO confessions(student_id,author_id,message,created_at) VALUES(?,?,?,?)",
            (student_id, user["id"], message, datetime.now(timezone.utc).isoformat()),
        )
    return RedirectResponse(f"/student/{student_id}", status_code=303)


@app.post("/like/{confession_id}")
def toggle_like(confession_id: int, request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    with connect() as con:
        confession = con.execute(
            "SELECT id, student_id FROM confessions WHERE id=?", (confession_id,)
        ).fetchone()
        if not confession:
            raise HTTPException(404, "Confession not found")

        existing = con.execute(
            "SELECT id FROM likes WHERE user_id=? AND confession_id=?",
            (user["id"], confession_id),
        ).fetchone()
        if existing:
            con.execute("DELETE FROM likes WHERE id=?", (existing["id"],))
        else:
            con.execute(
                "INSERT INTO likes(user_id,confession_id) VALUES(?,?)",
                (user["id"], confession_id),
            )

    return RedirectResponse(f"/student/{confession['student_id']}", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
