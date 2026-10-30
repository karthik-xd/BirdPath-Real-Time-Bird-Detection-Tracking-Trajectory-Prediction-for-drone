package com.birdpath.app

import com.birdpath.app.ml.ByteTracker
import com.birdpath.app.ml.TrackLifecycle
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ByteTrackerTest {

    @Test
    fun testTwoStageByteTrackAssociation() {
        val tracker = ByteTracker(highThresh = 0.5f, lowThresh = 0.1f, matchThresh = 0.3f)

        // Frame 1: High confidence detection -> creates 1 tentative track
        val frame1 = listOf(ByteTracker.Detection(100f, 100f, 50f, 40f, 0.85f))
        tracker.update(frame1)
        assertEquals(1, tracker.tracks.size)
        assertEquals(TrackLifecycle.TENTATIVE, tracker.tracks[0].state)

        // Frame 2: High confidence detection -> hits = 2
        val frame2 = listOf(ByteTracker.Detection(104f, 102f, 50f, 40f, 0.82f))
        tracker.update(frame2)
        assertEquals(2, tracker.tracks[0].hits)

        // Frame 3: Low confidence detection (e.g. motion blur, score = 0.35f) -> hits = 3 -> CONFIRMED
        val frame3 = listOf(ByteTracker.Detection(108f, 104f, 50f, 40f, 0.35f))
        val active = tracker.update(frame3)
        assertEquals(3, tracker.tracks[0].hits)
        assertEquals(TrackLifecycle.CONFIRMED, tracker.tracks[0].state)
        assertEquals(1, active.size)
    }

    @Test
    fun testTrackLifecycleLostAndRemovedAfter30Frames() {
        val tracker = ByteTracker(highThresh = 0.5f, lowThresh = 0.1f, maxTimeLost = 30)

        // Establish confirmed track (3 hits)
        for (i in 0 until 3) {
            tracker.update(listOf(ByteTracker.Detection(200f + i * 2, 200f, 50f, 40f, 0.9f)))
        }
        assertEquals(TrackLifecycle.CONFIRMED, tracker.tracks[0].state)

        // Miss detection for 30 frames
        for (f in 0 until 30) {
            tracker.update(emptyList())
        }
        assertEquals(1, tracker.tracks.size)
        assertEquals(TrackLifecycle.LOST, tracker.tracks[0].state)

        // 31st missed frame -> removed
        tracker.update(emptyList())
        assertEquals(0, tracker.tracks.size)
    }

    @Test
    fun testRingBufferCapacityLimit() {
        val tracker = ByteTracker()
        // 40 consecutive updates
        for (i in 0 until 40) {
            tracker.update(listOf(ByteTracker.Detection(100f + i, 100f, 30f, 30f, 0.9f)))
        }
        assertEquals(1, tracker.tracks.size)
        assertEquals(30, tracker.tracks[0].history.size)
    }
}
