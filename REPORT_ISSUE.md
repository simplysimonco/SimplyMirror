# How to report a build / runtime error (paste this back)

Copy-paste and fill in:

```
1. What I clicked / what I expected:
2. What happened instead (exact message or screenshot):
3. Where (tick one):
   [ ] PC app (MirrorHelper.exe / py app.py)
   [ ] build_exe.bat (making the exe)
   [ ] Android cloud build (GitHub Actions)
   [ ] Android app on phone
4. Paste here:
   - PC: whole of diagnostics-pc.txt (run collect_diagnostics.bat)
     + diagnostics-report.txt (button in app: Copy error report)
     + mirror-helper.log tail if asked
     + build.log tail if build failed (or attach build.log)
   - Android build: Actions run URL + the FAILED step log + download the
     `build-logs` artifact if present
   - Android app: tap Copy diagnostics in app, paste the text
```

Where the files live (PC, same folder as the app):
- `diagnostics-pc.txt` — made by double-clicking `collect_diagnostics.bat`
- `diagnostics-report.txt` + `mirror-helper.log` — made by the in-app button
- `build.log` — made by `build_exe.bat` (every run appends; always send tail on failure)
