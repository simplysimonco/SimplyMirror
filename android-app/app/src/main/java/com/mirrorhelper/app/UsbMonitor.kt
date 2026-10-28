package com.mirrorhelper.app

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager
import android.os.Build

/** Plain-language USB state for the wizard. No root, no special permission. */
object UsbMonitor {

    data class State(
        val usbPlugged: Boolean,
        val usbFunction: String,   // e.g. "mtp", "ptp", "rndis", "none", "unknown"
        val onTetheringNet: Boolean
    )

    fun current(ctx: Context): State {
        val batt = sticky(ctx, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val chargePlug = batt?.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0) ?: 0
        val usbPlugged = (chargePlug and BatteryManager.BATTERY_PLUGGED_USB) != 0

        var function = "unknown"
        try {
            // ACTION_USB_STATE sticky broadcast carries functions like "mtp,adb".
            val usb = sticky(ctx, IntentFilter("android.hardware.usb.action.USB_STATE"))
            val configured = usb?.getBooleanExtra("configured", false) ?: false
            function = usb?.getStringExtra("function") ?: usb?.getStringExtra("functions") ?: function
            if (!usbPlugged && !configured) function = "none"
        } catch (_: Exception) { }

        var tethered = false
        try {
            val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            val nets = cm.allNetworks.mapNotNull { cm.getNetworkCapabilities(it) }
            // USB tethering usually shows as TRANSPORT_ETHERNET on the phone side.
            tethered = nets.any {
                it.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) && usbPlugged
            }
        } catch (_: Exception) { }

        return State(usbPlugged, function, tethered)
    }

    fun advice(s: State): String = when {        !s.usbPlugged -> "Not plugged in yet. Plug your USB-C cable: phone → computer. Use the cable from the box."
        s.usbFunction.contains("mtp") -> "Perfect — computer can see your files. On the computer open This PC → your phone → Download → MirrorHelper."
        s.usbFunction.contains("ptp") -> "Cable is in photos mode. Swipe down on phone → tap USB → choose File Transfer."
        s.usbFunction.contains("rndis") || s.onTetheringNet -> "USB tethering is ON. On the computer open a browser to the address shown below."
        s.usbFunction == "none" -> "Plugged but not talking yet. Unlock phone, tap Allow if asked, set USB to File Transfer."
        else -> "Plugged in (${s.usbFunction}). If the computer can't see files: swipe down → USB → File Transfer."
    }

    fun isFileTransfer(s: State): Boolean = s.usbFunction.contains("mtp")

    // API 33+ requires an explicit export flag even for sticky queries.
    private fun sticky(ctx: Context, filter: IntentFilter): Intent? {
        return try {
            if (Build.VERSION.SDK_INT >= 33) {
                ctx.registerReceiver(null, filter, Context.RECEIVER_NOT_EXPORTED)
            } else {
                @Suppress("DEPRECATION")
                ctx.registerReceiver(null, filter)
            }
        } catch (_: Exception) { null }
    }
}
