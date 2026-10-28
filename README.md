# SimplyMirror — show your Android phone on your PC, with sound

Plug your phone into your computer with a USB cable → your phone screen + audio appear on the PC, controllable with mouse and keyboard. First setup takes ~5 minutes, afterwards it's one click.

## Downloads (get these from [Releases](../../releases))

- **PC (Windows):** `SimplyMirror.exe` — single file, nothing to install. Double-click to run.
- **Phone (Android) — pick one:**
  - `ScreenMirror-FullDrop.apk` (~34 MB) — PC helper built in, works even offline.
  - `ScreenMirror-SkyDrop.apk` (~1 MB) — tiny, downloads the PC helper on first run.

You need: a Windows PC, an Android phone, and a USB **data** cable (the one from the box — cheap charge-only cables won't work).

## Friend-proof setup (5 min, once)

1. Install the APK on your phone, open **SimplyMirror**, tap through the 4 big steps (it tells you exactly what to tap, including the hidden "tap Build number 7 times" switch).
2. Plug USB-C: phone → computer. On the phone pick **File Transfer**, tap **Allow** on the permission popup.
3. On the PC, run `SimplyMirror.exe` → click **SHOW MY PHONE ON PC NOW**. Done — next time just plug in + SHOW.

No USB-C video cable needed (laptop USB-C ports are video-OUT only, and DVI carries no sound). This mirrors over USB-data, so screen **and** audio both work.

## What's in this repo

- `app.py` → the PC Connector (built to `SimplyMirror.exe`, single-file, no install)
- `android-app/` → the phone companion APK source (Kotlin, targets API 36 for Play compliance)
- `phone_companion/` → printable/setup helper page served by the PC app over WiFi
- `.github/workflows/` → cloud build for APK + Play bundle (AAB) with deobfuscation mapping

## Sharing / testing

- Friends only need the two files from **Releases** — no Python, no Android Studio, nothing to build.
- Found a bug? PC app → **📋 Copy error report** button, phone app → same button — paste the text into an issue.
