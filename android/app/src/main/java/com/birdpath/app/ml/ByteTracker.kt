package com.birdpath.app.ml

import java.util.ArrayDeque
import kotlin.math.max
import kotlin.math.min

enum class TrackLifecycle {
    TENTATIVE,
    CONFIRMED,
    LOST,
    REMOVED
}

class Track(
    val id: Int,
    initialBox: FloatArray, // [cx, cy, w, h]
    var score: Float
) {
    val kalman = KalmanFilter(initialBox)
    var state = TrackLifecycle.TENTATIVE
    var hits = 1
    var age = 0
    var timeSinceUpdate = 0
    var lostSinceMs = 0L

    // 30-frame ring buffer of past [cx, cy, w, h]
    val history = ArrayDeque<FloatArray>(30)

    init {
        history.addLast(initialBox.clone())
    }

    fun predict(): FloatArray {
        val predicted = kalman.predict()
        age++
        timeSinceUpdate++
        return predicted
    }

    fun update(box: FloatArray, detectionScore: Float) {
        kalman.update(box)
        this.score = detectionScore
        timeSinceUpdate = 0
        hits++

        if (state == TrackLifecycle.TENTATIVE && hits >= 3) {
            state = TrackLifecycle.CONFIRMED
        }

        if (history.size >= 30) {
            history.removeFirst()
        }
        history.addLast(kalman.getBox())
    }

    fun getBox(): FloatArray = kalman.getBox()
}

/**
 * ByteTracker
 * Multi-object tracker using ByteTrack 2-stage association:
 * - High-confidence detections matched first to tracks using IoU
 * - Low-confidence detections matched second to remaining unmatched tracks
 * - Tentative tracks confirmed after 3 hits, kept for 30 missed frames before removal
 */
class ByteTracker(
    private val highThresh: Float = 0.50f,
    private val lowThresh: Float = 0.10f,
    private val matchThresh: Float = 0.40f,
    private val maxTimeLost: Int = 30
) {
    private var nextTrackId = 1
    val tracks = mutableListOf<Track>()

    data class Detection(
        val cx: Float,
        val cy: Float,
        val w: Float,
        val h: Float,
        val score: Float
    ) {
        fun toBoxArray(): FloatArray = floatArrayOf(cx, cy, w, h)
    }

    fun update(detections: List<Detection>): List<Track> {
        // Step 1: Project all tracks forward with Kalman prediction
        for (t in tracks) {
            t.predict()
        }

        // Step 2: Split detections into High and Low score groups
        val highDets = detections.filter { it.score >= highThresh }
        val lowDets = detections.filter { it.score in lowThresh..<highThresh }

        // Stage 1: Match High detections to existing tracks
        val (matchedT1, unmatchedT1, unmatchedD1) = associate(tracks, highDets, matchThresh)
        for ((tIdx, dIdx) in matchedT1) {
            tracks[tIdx].update(highDets[dIdx].toBoxArray(), highDets[dIdx].score)
        }

        // Stage 2: Match Low detections to still-unmatched tracks
        val remainingTracks = unmatchedT1.map { tracks[it] }
        val (matchedT2, unmatchedT2, _) = associate(remainingTracks, lowDets, matchThresh)
        for ((remTIdx, dIdx) in matchedT2) {
            remainingTracks[remTIdx].update(lowDets[dIdx].toBoxArray(), lowDets[dIdx].score)
        }

        // Mark still-unmatched tracks as LOST
        val now = System.currentTimeMillis()
        for (remTIdx in unmatchedT2) {
            val t = remainingTracks[remTIdx]
            if (t.state == TrackLifecycle.CONFIRMED) {
                t.state = TrackLifecycle.LOST
                if (t.lostSinceMs == 0L) t.lostSinceMs = now
            } else if (t.state == TrackLifecycle.TENTATIVE) {
                t.state = TrackLifecycle.REMOVED
            }
        }

        // Create new tentative tracks from unmatched High detections
        for (dIdx in unmatchedD1) {
            val det = highDets[dIdx]
            val newTrack = Track(nextTrackId++, det.toBoxArray(), det.score)
            tracks.add(newTrack)
        }

        // Clean up tracks lost beyond maxTimeLost frames
        tracks.removeAll { it.timeSinceUpdate > maxTimeLost || it.state == TrackLifecycle.REMOVED }

        // Return active tracks (confirmed or recently lost)
        return tracks.filter { it.state == TrackLifecycle.CONFIRMED || it.state == TrackLifecycle.LOST }
    }

    private fun associate(
        trackList: List<Track>,
        detList: List<Detection>,
        threshold: Float
    ): Triple<List<Pair<Int, Int>>, List<Int>, List<Int>> {
        if (trackList.isEmpty() || detList.isEmpty()) {
            return Triple(emptyList(), trackList.indices.toList(), detList.indices.toList())
        }

        val costMatrix = Array(trackList.size) { FloatArray(detList.size) }
        for (i in trackList.indices) {
            val tb = trackList[i].getBox()
            for (j in detList.indices) {
                val db = detList[j].toBoxArray()
                costMatrix[i][j] = 1.0f - calculateIoU(tb, db)
            }
        }

        // Hungarian algorithm / minimum cost matching
        val matches = minCostMatching(costMatrix, 1.0f - threshold)
        val matchedTracks = matches.map { it.first }.toSet()
        val matchedDets = matches.map { it.second }.toSet()

        val unmatchedTracks = trackList.indices.filter { it !in matchedTracks }
        val unmatchedDets = detList.indices.filter { it !in matchedDets }

        return Triple(matches, unmatchedTracks, unmatchedDets)
    }

    companion object {
        fun calculateIoU(b1: FloatArray, b2: FloatArray): Float {
            val b1X1 = b1[0] - b1[2] / 2.0f
            val b1Y1 = b1[1] - b1[3] / 2.0f
            val b1X2 = b1[0] + b1[2] / 2.0f
            val b1Y2 = b1[1] + b1[3] / 2.0f

            val b2X1 = b2[0] - b2[2] / 2.0f
            val b2Y1 = b2[1] - b2[3] / 2.0f
            val b2X2 = b2[0] + b2[2] / 2.0f
            val b2Y2 = b2[1] + b2[3] / 2.0f

            val ix1 = max(b1X1, b2X1)
            val iy1 = max(b1Y1, b2Y1)
            val ix2 = min(b1X2, b2X2)
            val iy2 = min(b1Y2, b2Y2)

            val iw = max(0.0f, ix2 - ix1)
            val ih = max(0.0f, iy2 - iy1)
            val interArea = iw * ih

            val area1 = b1[2] * b1[3]
            val area2 = b2[2] * b2[3]
            val union = area1 + area2 - interArea

            return if (union <= 0.0f) 0.0f else interArea / union
        }

        /**
         * Greedy minimum-cost bipartite assignment for real-time mobile latency.
         */
        fun minCostMatching(cost: Array<FloatArray>, maxCost: Float): List<Pair<Int, Int>> {
            val rows = cost.size
            val cols = cost[0].size
            val matches = mutableListOf<Pair<Int, Int>>()

            val rowUsed = BooleanArray(rows)
            val colUsed = BooleanArray(cols)

            // Extract all candidate pairs sorted by increasing cost
            val candidates = mutableListOf<Triple<Int, Int, Float>>()
            for (r in 0 until rows) {
                for (c in 0 until cols) {
                    if (cost[r][c] <= maxCost) {
                        candidates.add(Triple(r, c, cost[r][c]))
                    }
                }
            }
            candidates.sortBy { it.third }

            for ((r, c, _) in candidates) {
                if (!rowUsed[r] && !colUsed[c]) {
                    rowUsed[r] = true
                    colUsed[c] = true
                    matches.add(Pair(r, c))
                }
            }

            return matches
        }
    }
}
