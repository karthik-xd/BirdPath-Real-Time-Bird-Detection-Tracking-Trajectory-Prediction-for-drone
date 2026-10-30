package com.birdpath.app.sensor

import com.birdpath.app.ml.Track
import com.birdpath.app.ml.TrackLifecycle

/**
 * FrameSkipController
 * Dynamically throttles heavy YOLO neural network execution when hardware
 * cannot sustain 20+ FPS, while ensuring the 8-state Kalman Filter updates
 * every single frame for continuous, low-latency tracking.
 */
class FrameSkipController(
    private val targetFps: Float = 20.0f
) {
    private var skipCounter = 0
    private var maxSkipFrames = 1

    fun shouldRunDetector(activeTracks: List<Track>, lastInferenceMs: Long): Boolean {
        // Always run detector if no confirmed tracks exist
        val confirmedTracks = activeTracks.filter { it.state == TrackLifecycle.CONFIRMED }
        if (confirmedTracks.isEmpty()) {
            skipCounter = 0
            return true
        }

        // If any track is lost or has low score, force detector immediately
        val hasUnstableTrack = activeTracks.any {
            it.state == TrackLifecycle.LOST || it.score < 0.40f
        }
        if (hasUnstableTrack) {
            skipCounter = 0
            return true
        }

        // Check if latency is exceeding budget (1000ms / 20fps = 50ms)
        val budgetMs = (1000.0f / targetFps).toLong()
        if (lastInferenceMs > budgetMs) {
            maxSkipFrames = if (lastInferenceMs > 75) 2 else 1
            if (skipCounter < maxSkipFrames) {
                skipCounter++
                return false // Skip detector this frame; keep Kalman updating!
            }
        }

        skipCounter = 0
        return true
    }
}
