package com.mirrorhelper.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.widget.Toast

/** Fired from the PC after the user double-clicks the connector:
 *  adb shell am broadcast -a com.mirrorhelper.PC_CONNECTED
 */
class PcConnectedReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == ACTION) {
            val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            prefs.edit().putBoolean(KEY_CONNECTED, true).apply()
            Toast.makeText(context, "PC connected! Mirror should be on your computer.", Toast.LENGTH_LONG).show()
            // Bring wizard to success step if app is in foreground.
            val launch = Intent(context, MainActivity::class.java)
            launch.action = ACTION
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            try { context.startActivity(launch) } catch (_: Exception) { }
        }
    }

    companion object {
        const val ACTION = "com.mirrorhelper.PC_CONNECTED"
        const val PREFS = "mirror_helper"
        const val KEY_CONNECTED = "pc_connected"
    }
}
