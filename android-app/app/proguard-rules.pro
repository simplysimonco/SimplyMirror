# Keep the app entry point + handshake receiver (R8 would otherwise rename them).
-keep class com.mirrorhelper.app.MainActivity { *; }
-keep class com.mirrorhelper.app.PcConnectedReceiver { *; }
-keep class com.mirrorhelper.app.UsbMonitor { *; }
-keep class com.mirrorhelper.app.PcPackageServer { *; }

# Keep broadcast action string referenced via adb.
-keepnames class * extends android.content.BroadcastReceiver

# Standard Android rules.
-keepattributes *Annotation*,Signature,InnerClasses,EnclosingMethod
-dontwarn java.lang.invoke.**
