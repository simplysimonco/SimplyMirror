# Mirror Helper — mobile-first architecture

## Direction (new): phone leads, PC follows

1. User installs APK on Android first. All hand-holding lives in the phone app.
2. Phone prepares the PC package (downloads `MirrorHelper.exe` once, stages it where the PC can see it).
3. User plugs USB-C phone -> PC. Phone detects USB, walks user to ONE click on PC.
4. PC Connector runs, signals back to phone over adb, mirror starts.

## Why not zero-click push?

USB roles: PC = host, phone = device. Stock Windows will NEVER auto-execute
a file pushed from a phone (AutoRun on USB was killed in Win7 — Conficker worm).
Any product claiming "plug phone, PC auto-installs, no click" is either:

- lying, or
- shipping a custom USB driver / enterprise MDM, or
- actually using MTP + 1 double-click and calling it "push".

So we implement the honest version that *feels* like a push:

- APK copies `MirrorHelper.exe` to public `Download/MirrorHelper/` (visible on PC
  instantly via MTP as `This PC > Phone > Download > MirrorHelper`).
- APK optionally starts a USB-tethering web server (`http://192.168.42.129:8080`)
  serving the same exe — backup path if MTP is confusing.
- Phone screen shows live USB state (disconnected / charging-only / file-transfer /
  tethering) and tells the user exactly what to tap.
- On PC the user does exactly ONE double-click. After that the PC Connector sends
  `adb shell am broadcast -a com.mirrorhelper.PC_CONNECTED` so the phone UI flips
  to "Connected 🎉" with no further work.

## Repo layout

- `android-app/` — APK source (Kotlin, no external deps). Build via GitHub Actions.
- `../app.py` — PC Connector (updated: sends handshake broadcast to phone on start).
- `../phone_companion/companion.html` — fallback if user has no APK yet.
- `.github/workflows/build-apk.yml` — cloud build, download artifact, sideload.

## Build the APK + AAB (no local SDK needed)

1. Push this folder to a GitHub repo.
2. Actions tab -> `Build APK + AAB (Play: target 36)` -> Run.
3. Download artifacts:
   - `MirrorHelper-app-debug` (app-debug.apk — sideload for testing)
   - `MirrorHelper-release-aab` (app-release.aab — upload to Play)
   - `deobfuscation-mapping` (mapping.txt — upload to Play, same release)
   - `native-debug-symbols` (only if present — upload to Play)
   - `build-logs` (gradle-build.log + reports — paste back on failure)
4. Alternative local: JDK 17 + cmdline-tools, run `gradle assembleDebug bundleRelease`.

## Play upload checklist (same bar as SimplyTimer v9)

Your screenshot's 1 error + 2 warnings map exactly:

- [ ] Error "must target at least API level 36": fixed — `compileSdk 36`,
      `targetSdk 36` in `app/build.gradle`. CI fails fast if binary reports < 36.
- [ ] Warning "no deobfuscation file": fixed — `minifyEnabled true` in release
      generates `mapping.txt`. Upload the `deobfuscation-mapping` artifact
      on the same Play release (App bundle explorer -> ReTrace mapping file).
- [ ] Warning "no debug symbols": fixed — app has zero native `.so`
      (stdlib only), plus `ndk { debugSymbolLevel 'FULL' }` so IF a future
      dependency adds `.so`, `native-debug-symbols.zip` is produced.
      Upload it if the artifact exists; otherwise the warning does not apply.

Play steps: Release -> Create release -> upload `app-release.aab` ->
add `mapping.txt` under "Deobfuscation files" -> add symbols under
"Native debug symbols" if present -> Rollout. Keep `versionCode` bumping
(current: 2) for every Play upload.

## First-run data flow

```
[APK first launch]
  -> download MirrorHelper.exe from GitHub Releases to app storage
  -> copy to Download/MirrorHelper/MirrorHelper.exe (MediaStore, visible over MTP)
  -> show Step 2: "plug USB-C now"
[USB plugged]
  -> UsbMonitor detects state, prompts File Transfer + Allow RSA
[User double-clicks exe on PC]
  -> PC Connector runs adb start-server, adb devices, scrcpy
  -> PC runs: adb shell am broadcast -a com.mirrorhelper.PC_CONNECTED
  -> Phone receiver shows success, onboarding completes
```
