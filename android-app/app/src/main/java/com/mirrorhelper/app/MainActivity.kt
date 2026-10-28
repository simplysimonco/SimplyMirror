package com.mirrorhelper.app

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : Activity() {

    // PC Connector lives in the SimplyMirror GitHub release as SimplyMirror.exe.
    private val PC_EXE_URL =
        "https://github.com/simplysimonco/SimplyMirror/releases/latest/download/SimplyMirror.exe"
    private val PC_EXE_NAME = "SimplyMirror.exe"

    private var step = 0 // 0..4
    private lateinit var root: LinearLayout
    private lateinit var titleView: TextView
    private lateinit var bodyView: TextView
    private lateinit var statusView: TextView
    private lateinit var progress: ProgressBar
    private lateinit var backBtn: Button
    private lateinit var nextBtn: Button
    private lateinit var actionBtn: Button

    private var stagedExe: File? = null
    private var server: PcPackageServer? = null

    private val usbReceiver = object : BroadcastReceiver() {
        override fun onReceive(c: Context, i: Intent) { refreshUsbStatus() }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(usbReceiver, IntentFilter("android.hardware.usb.action.USB_STATE"), Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("DEPRECATION")
            registerReceiver(usbReceiver, IntentFilter("android.hardware.usb.action.USB_STATE"))
        }
        render()
        thread { stagedExe = findStagedExe() }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        if (intent.action == PcConnectedReceiver.ACTION) {
            step = 4
            render()
        }
    }

    override fun onDestroy() {
        try { unregisterReceiver(usbReceiver) } catch (_: Exception) { }
        server?.stop()
        super.onDestroy()
    }

    // ---------------- UI (all programmatic, beginner-big) ----------------
    private fun buildUi() {
        val scroll = ScrollView(this)
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 48, 48, 48)
        }
        scroll.addView(root)
        setContentView(scroll)

        val head = TextView(this).apply {
            text = "SimplyMirror"
            textSize = 30f
            setTypeface(typeface, Typeface.BOLD)
            gravity = Gravity.CENTER
        }
        root.addView(head)

        titleView = TextView(this).apply {
            textSize = 22f
            setTypeface(typeface, Typeface.BOLD)
            setPadding(0, 24, 0, 8)
        }
        root.addView(titleView)

        bodyView = TextView(this).apply { textSize = 18f }
        root.addView(bodyView)

        actionBtn = Button(this).apply {
            textSize = 18f
            visibility = View.GONE
        }
        root.addView(actionBtn)

        statusView = TextView(this).apply {
            textSize = 16f
            setPadding(0, 16, 0, 0)
        }
        root.addView(statusView)

        progress = ProgressBar(this).apply { visibility = View.GONE }
        root.addView(progress)

        val nav = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 32, 0, 0)
        }
        backBtn = Button(this).apply { text = "← Back"; setOnClickListener { step = (step - 1).coerceAtLeast(0); render() } }
        nextBtn = Button(this).apply { text = "Next →"; setOnClickListener { step = (step + 1).coerceAtMost(4); render() } }
        nav.addView(backBtn, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        nav.addView(nextBtn, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        root.addView(nav)

        val diag = Button(this).apply {
            text = "📋 Copy diagnostics for help"
            textSize = 14f
            setOnClickListener { copyDiagnostics() }
        }
        root.addView(diag)
        val hint = TextView(this).apply {
            text = "If anything fails, tap above, then paste the text back for debugging."
            textSize = 13f
        }
        root.addView(hint)
    }

    private fun copyDiagnostics() {
        try {
            val s = try { UsbMonitor.current(this) } catch (e: Exception) { null }
            val prefs = getSharedPreferences(PcConnectedReceiver.PREFS, MODE_PRIVATE)
            val sb = StringBuilder()
            sb.appendLine("=== SimplyMirror phone diagnostics ===")
            sb.appendLine("Android ${Build.VERSION.RELEASE} (SDK ${Build.VERSION.SDK_INT}) ${Build.MANUFACTURER} ${Build.MODEL}")
            sb.appendLine("App step=$step pc_connected=${prefs.getBoolean(PcConnectedReceiver.KEY_CONNECTED, false)}")
            sb.appendLine("USB plugged=${s?.usbPlugged} function=${s?.usbFunction} tetherNet=${s?.onTetheringNet}")
            val f = stagedExe ?: findStagedExe()
            sb.appendLine("Staged exe: ${f?.absolutePath ?: "(none)"} exists=${f?.exists() == true} size=${if (f?.exists() == true) f.length() else 0}")
            sb.appendLine("Server running=${server?.running == true}")
            sb.appendLine("URL=$PC_EXE_URL")
            sb.appendLine("=== end: paste everything above back for help ===")
            val text = sb.toString()
            val cm = getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
            cm.setPrimaryClip(android.content.ClipData.newPlainText("diagnostics", text))
            Toast.makeText(this, "Copied. Paste it back for help.", Toast.LENGTH_LONG).show()
            // also offer share sheet
            try {
                val share = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"; putExtra(Intent.EXTRA_TEXT, text)
                }
                startActivity(Intent.createChooser(share, "Send diagnostics"))
            } catch (_: Exception) { }
        } catch (e: Exception) {
            Toast.makeText(this, "Diagnostics failed: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    private fun render() {
        actionBtn.visibility = View.GONE
        progress.visibility = View.GONE
        backBtn.visibility = if (step == 0) View.GONE else View.VISIBLE
        nextBtn.text = if (step == 4) "Restart" else "Next →"
        if (step == 4 && nextBtn.text == "Restart") {
            nextBtn.setOnClickListener { step = 0; render() }
        } else {
            nextBtn.setOnClickListener { step = (step + 1).coerceAtMost(4); render() }
        }

        when (step) {
            0 -> {
                titleView.text = "Step 1 of 4: Welcome 👋"
                bodyView.text = "This app puts your phone screen on your computer, with sound.\n\n" +
                    "You only do this once (5 minutes). After that: plug cable → mirror.\n\n" +
                    "You need: this phone + a USB cable (the one from the box is best)."
                statusView.text = ""
                actionBtn.visibility = View.GONE
            }
            1 -> {
                titleView.text = "Step 2 of 4: Get the computer part ready"
                bodyView.text = "Your computer needs a small helper (SimplyMirror.exe).\n\n" +
                    "Tap the button below. I will download it and place it where your " +
                    "computer can see it (Download folder). One tap, then wait."
                actionBtn.visibility = View.VISIBLE
                actionBtn.text = "⬇ Prepare computer helper"
                actionBtn.setOnClickListener { preparePcPackage() }
                val f = stagedExe
                statusView.text = if (f != null && f.exists())
                    "✅ Ready: ${f.name} (${f.length() / 1024 / 1024} MB) staged for your PC."
                else "Not downloaded yet."
            }
            2 -> {
                titleView.text = "Step 3 of 4: Plug in + tap Allow"
                bodyView.text = "1. Plug USB-C: this phone → computer.\n" +
                    "2. Unlock this phone.\n" +
                    "3. Swipe down → tap USB → choose File Transfer.\n" +
                    "4. If asked “Allow USB debugging?” tick Always allow → Allow.\n\n" +
                    "Need the hidden switch first? Tap below."
                actionBtn.visibility = View.VISIBLE
                actionBtn.text = "⚙ Open settings for me"
                actionBtn.setOnClickListener {
                    try {
                        startActivity(Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS))
                    } catch (_: Exception) {
                        try { startActivity(Intent(Settings.ACTION_DEVICE_INFO_SETTINGS)) } catch (_: Exception) {
                            Toast.makeText(this, "Open Settings → About phone → tap Build number 7 times", Toast.LENGTH_LONG).show()
                        }
                    }
                }
                refreshUsbStatus()
            }
            3 -> {
                titleView.text = "Step 4 of 4: One click on the computer"
                bodyView.text = "Windows never lets a phone install things by itself " +
                    "(virus protection). So there is exactly ONE click left:\n\n" +
                    "On the COMPUTER open: This PC → your phone → Download → SimplyMirror → " +
                    "double-click SimplyMirror.exe → click SHOW MY PHONE.\n\n" +
                    "No File Transfer? Use the backup: turn on USB tethering on this phone, " +
                    "then on the computer open the address below."
                actionBtn.visibility = View.VISIBLE
                actionBtn.text = "🌐 Start backup download link"
                actionBtn.setOnClickListener { startServer() }
                refreshUsbStatus()
            }
            4 -> {
                val connected = getSharedPreferences(PcConnectedReceiver.PREFS, MODE_PRIVATE)
                    .getBoolean(PcConnectedReceiver.KEY_CONNECTED, false)
                titleView.text = if (connected) "🎉 Connected!" else "Almost there…"
                bodyView.text = if (connected)
                    "Your computer said hello. The mirror window should be open on your PC.\n\nNext time: just plug in and double-click SimplyMirror.exe."
                else
                    "I have not heard from your computer yet.\n\nDouble-click SimplyMirror.exe on the PC first. " +
                    "The moment it runs, this screen turns green automatically."
                statusView.text = if (connected) "✅ PC handshake received." else "Waiting for PC…"
            }
        }
    }

    // ---------------- USB + staging ----------------
    private fun refreshUsbStatus() {
        if (!::statusView.isInitialized) return
        if (step != 2 && step != 3) return
        val s = UsbMonitor.current(this)
        val extra = if (step == 3) {
            val srv = server
            if (srv?.running == true) "\n\nBackup link is ON. On PC browser open:\nhttp://192.168.42.129:8080\n(if that fails, check the IP in phone Settings → USB tethering help)."
            else ""
        } else ""
        statusView.text = "📱 Phone USB: " + UsbMonitor.advice(s) + extra
    }

    private fun findStagedExe(): File? {
        // 1. private storage (always writable)
        val priv = File(getExternalFilesDir(null), PC_EXE_NAME)
        if (priv.exists() && priv.length() > 1_000_000) return priv
        // 2. public Download/SimplyMirror (visible over MTP on PC)
        val pub = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "SimplyMirror/$PC_EXE_NAME")
        if (pub.exists() && pub.length() > 1_000_000) return pub
        return null
    }

    private fun preparePcPackage() {
        progress.visibility = View.VISIBLE
        statusView.text = "Downloading… please wait (one time, ~30 MB)."
        thread {
            try {
                val priv = File(getExternalFilesDir(null), PC_EXE_NAME)
                if (!priv.exists() || priv.length() < 1_000_000) {
                    downloadTo(PC_EXE_URL, priv)
                }
                stagedExe = priv
                copyToPublicDownload(priv)
                runOnUiThread {
                    progress.visibility = View.GONE
                    statusView.text = "✅ Ready: placed where your computer can see it.\nNow go to Step 3 (plug in)."
                    Toast.makeText(this, "Computer helper is ready", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                runOnUiThread {
                    progress.visibility = View.GONE
                    statusView.text = "Download failed: ${e.message}\n\n" +
                        "Fix: connect phone to WiFi and try again. URL:\n$PC_EXE_URL"
                }
            }
        }
    }

    private fun downloadTo(url: String, dest: File) {
        dest.parentFile?.mkdirs()
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.instanceFollowRedirects = true
        conn.connectTimeout = 30000
        conn.connect()
        if (conn.responseCode !in 200..299) throw Exception("HTTP ${conn.responseCode}")
        conn.inputStream.use { input ->
            FileOutputStream(dest).use { output -> input.copyTo(output) }
        }
    }

    private fun copyToPublicDownload(src: File) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, PC_EXE_NAME)
                    put(MediaStore.Downloads.RELATIVE_PATH, "Download/SimplyMirror")
                    put(MediaStore.Downloads.MIME_TYPE, "application/octet-stream")
                }
                val uri: Uri? = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                if (uri != null) {
                    contentResolver.openOutputStream(uri)?.use { out -> src.inputStream().copyTo(out) }
                }
            } else {
                @Suppress("DEPRECATION")
                val pub = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "SimplyMirror/$PC_EXE_NAME")
                pub.parentFile?.mkdirs()
                src.copyTo(pub, overwrite = true)
            }
        } catch (e: Exception) {
            // Non-fatal: private copy still lets the HTTP-server path work.
            android.util.Log.w("SimplyMirror", "public copy failed: $e")
        }
    }

    private fun startServer() {
        val f = stagedExe ?: findStagedExe()
        if (f == null || !f.exists()) {
            Toast.makeText(this, "Tap «Prepare computer helper» first (Step 2).", Toast.LENGTH_LONG).show()
            step = 1; render(); return
        }
        if (server?.running == true) {
            refreshUsbStatus(); return
        }
        server = PcPackageServer(f, 8080)
        server?.start()
        Toast.makeText(this, "Backup link started on port 8080", Toast.LENGTH_SHORT).show()
        refreshUsbStatus()
    }
}
