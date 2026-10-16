# BearTracks Sniper

Watches a full course in BearTracks Schedule Builder and enrolls you automatically when a seat opens.
Optionally pings you on Discord.

## Before you start

1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/).
   On Windows, tick **"Add python.exe to PATH"** in the installer.
2. In BearTracks **Schedule Builder**, add the course you want to your courses and set up the
   schedule so that clicking "Get this Schedule" would enroll you in the right section.
   The sniper presses that button for you when a seat opens.

## Run it

- **Windows:** double-click `run.bat`
- **macOS / Linux:** open a terminal in this folder and run `bash run.sh`

The first run installs everything it needs, then asks for:

- your CCID and password
- the course to watch, written the way Schedule Builder shows it (e.g. `INT D 249`)
- a Discord webhook URL (optional, press Enter to skip)

A browser window opens and logs you in. Approve MFA there if asked. The first time, you also
pick the term in the terminal. After that, leave both windows open. The sniper checks every
30 seconds and logs back in by itself if BearTracks signs you out.

Press **Ctrl+C** in the terminal to stop.

## Changing settings

Every setting is in one file, `.env`, in this folder. It's created on the first run from
`.env.example`, and each line has a comment explaining it. That includes your login, the course,
the term, Discord alerts, and how often it checks. Open it in any text editor to change things.
If you empty a required value, the sniper asks for it again next time. Delete the whole file to
start setup over.

`.env` holds your password in plain text, so **never send that file to anyone.**
Send the folder without it, or share the GitHub link instead.

## Discord alerts (optional)

In a Discord server you own: **Server Settings → Integrations → Webhooks → New Webhook → Copy Webhook URL**.
To get pinged, also give it your user ID: turn on **Settings → Advanced → Developer Mode**,
then right-click your name and choose **Copy User ID**.
