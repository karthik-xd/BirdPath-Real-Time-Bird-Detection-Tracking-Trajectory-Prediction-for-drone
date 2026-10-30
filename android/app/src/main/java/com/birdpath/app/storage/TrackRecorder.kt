package com.birdpath.app.storage

import android.content.Context
import com.birdpath.app.ml.Track
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * TrackRecorder
 * Records timestamps, detected bounding boxes, and track identities to structured JSON.
 * Closes the active learning loop by feeding phone recordings back into dataset_builder.py.
 */
class TrackRecorder(private val context: Context) {

    private var isRecording = false
    private var sessionStartTime = 0L
    private val recordedTrackMap = mutableMapOf<Int, MutableList<BoxRecord>>()

    data class BoxRecord(
        val timestampMs: Long,
        val cx: Float,
        val cy: Float,
        val w: Float,
        val h: Float,
        val score: Float
    )

    fun startRecording(): String {
        isRecording = true
        sessionStartTime = System.currentTimeMillis()
        recordedTrackMap.clear()
        val timeStr = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date(sessionStartTime))
        return "session_$timeStr"
    }

    fun recordFrame(activeTracks: List<Track>, frameW: Float, frameH: Float) {
        if (!isRecording) return

        val now = System.currentTimeMillis()
        val relTime = now - sessionStartTime

        for (track in activeTracks) {
            val box = track.getBox()
            val record = BoxRecord(
                timestampMs = relTime,
                cx = box[0] / frameW,
                cy = box[1] / frameH,
                w = box[2] / frameW,
                h = box[3] / frameH,
                score = track.score
            )
            val list = recordedTrackMap.getOrPut(track.id) { mutableListOf() }
            list.add(record)
        }
    }

    fun stopRecording(): File? {
        if (!isRecording) return null
        isRecording = false

        val timeStr = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date(sessionStartTime))
        val exportDir = context.getExternalFilesDir("recorded_tracks") ?: context.filesDir
        val file = File(exportDir, "bird_tracks_$timeStr.json")

        val rootJson = JSONObject()
        rootJson.put("session_id", "session_$timeStr")
        rootJson.put("timestamp_start", sessionStartTime)

        val tracksArray = JSONArray()
        for ((trackId, boxes) in recordedTrackMap) {
            val trackObj = JSONObject()
            trackObj.put("track_id", trackId)

            val boxesArray = JSONArray()
            for (b in boxes) {
                val bObj = JSONObject()
                bObj.put("t", b.timestampMs)
                bObj.put("cx", b.cx.toDouble())
                bObj.put("cy", b.cy.toDouble())
                bObj.put("w", b.w.toDouble())
                bObj.put("h", b.h.toDouble())
                bObj.put("score", b.score.toDouble())
                boxesArray.put(bObj)
            }
            trackObj.put("boxes", boxesArray)
            tracksArray.put(trackObj)
        }
        rootJson.put("tracks", tracksArray)

        FileWriter(file).use { writer ->
            writer.write(rootJson.toString(2))
        }

        return file
    }

    fun isRecording(): Boolean = isRecording
}
