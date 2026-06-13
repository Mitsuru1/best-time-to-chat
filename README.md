# Best Time to Chat

A small Flask app for two friends to log daily availability and energy, then find the best overlapping time to message.

## Features

- Exactly two local profiles with username and numeric PIN login.
- Morning Person and Night Owl profile themes.
- Eight daily time slots from early morning through overnight.
- Per-slot status: Free, Maybe, or Busy.
- Optional energy rating from 1 to 5, defaulting to 3.
- Shared recommendation using both friends' entries.
- Last 7 days of personal history plus shared recommendation history.
- SQLite storage through SQLAlchemy.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Initialize the database:

```powershell
flask --app app init-db
```

Run the app:

```powershell
flask --app app run --port 5050
```

Open `http://127.0.0.1:5050`.

## First Use

1. Create the first profile.
2. Log out or use the setup link from login to create the second profile.
3. Each friend logs in with their username and PIN.
4. Each person fills out all 8 slots for the day.
5. Visit Results to see the ranked chat windows.

## Scoring

For each slot:

- If either friend is Busy, the score is 0.
- Free uses a 1.0 weight.
- Maybe uses a 0.6 weight.
- The app averages the two weighted energy ratings.
- The top one or two non-zero slots are highlighted as the best chat time.
