package com.mirrorhelper.app

import java.io.BufferedReader
import java.io.File
import java.io.FileInputStream
import java.io.InputStreamReader
import java.io.OutputStream
import java.net.ServerSocket
import kotlin.concurrent.thread

/**
 * Tiny HTTP server with zero dependencies. Serves ONE file (the PC exe)
 * plus a small landing page. Used over USB tethering as a backup path
 * when MTP is confusing: user opens http://192.168.42.129:PORT on the PC.
 */
class PcPackageServer(
    private val fileToServe: File,
    private val port: Int = 8080
) {
    @Volatile var running = false
    private var socket: ServerSocket? = null

    fun start() {
        if (running) return
        running = true
        thread(name = "pc-package-server", isDaemon = true) {
            try {
                socket = ServerSocket(port)
                while (running) {
                    val client = try { socket!!.accept() } catch (_: Exception) { break }
                    thread(isDaemon = true) { handle(client.getInputStream().bufferedReader(), client.getOutputStream()) }
                }
            } catch (_: Exception) { } finally { running = false }
        }
    }

    fun stop() {
        running = false
        try { socket?.close() } catch (_: Exception) { }
    }

    private fun handle(reader: BufferedReader, out: OutputStream) {
        try {
            val requestLine = reader.readLine() ?: return
            // consume headers
            while (true) { val h = reader.readLine() ?: break; if (h.isEmpty()) break }
            val path = requestLine.split(" ").getOrNull(1) ?: "/"

            if (path.startsWith("/download") || path.endsWith(".exe")) {
                serveFile(out)
            } else {
                val html = """
                    <html><body style="font-family:sans-serif;padding:24px">
                    <h1>Mirror Helper — PC Connector</h1>
                    <p>Step 1 of 1 on this computer: click the button, then Run.</p>
                    <p><a href="/download" style="font-size:22px">Download MirrorHelper.exe</a></p>
                    <p>File: ${fileToServe.name} (${fileToServe.length() / 1024 / 1024} MB)</p>
                    </body></html>
                """.trimIndent().toByteArray()
                write(out, "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: ${html.size}\r\nConnection: close\r\n\r\n", html)
            }
        } catch (_: Exception) { } finally { try { out.close() } catch (_: Exception) { } }
    }

    private fun serveFile(out: OutputStream) {
        val header = "HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\n" +
            "Content-Disposition: attachment; filename=\"${fileToServe.name}\"\r\n" +
            "Content-Length: ${fileToServe.length()}\r\nConnection: close\r\n\r\n"
        out.write(header.toByteArray())
        FileInputStream(fileToServe).use { it.copyTo(out) }
        out.flush()
    }

    private fun write(out: OutputStream, header: String, body: ByteArray) {
        out.write(header.toByteArray())
        out.write(body)
        out.flush()
    }
}
