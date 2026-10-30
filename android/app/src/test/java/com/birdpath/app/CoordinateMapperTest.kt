package com.birdpath.app

import com.birdpath.app.ui.CoordinateMapper
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CoordinateMapperTest {

    @Test
    fun testUnletterboxBoxCenterAligned() {
        // Raw frame 1920x1080 (16:9), target model size 640x640
        // Scale = 640 / 1920 = 0.333333
        // New H = 1080 * (640/1920) = 360, padY = (640 - 360)/2 = 140
        val mapper = CoordinateMapper(
            frameWidth = 1920,
            frameHeight = 1080,
            modelInputWidth = 640,
            modelInputHeight = 640
        )

        // Center of model 640x640 is (320, 320)
        val unletterboxed = mapper.unletterboxBox(320.0f, 320.0f, 64.0f, 36.0f)

        // Expected center in raw frame is (960, 540)
        assertEquals(960.0f, unletterboxed[0], 1.0f)
        assertEquals(540.0f, unletterboxed[1], 1.0f)
        assertEquals(192.0f, unletterboxed[2], 1.0f)
        assertEquals(108.0f, unletterboxed[3], 1.0f)
    }

    @Test
    fun testSensorRotation90Degrees() {
        val (xRot, yRot, rotW, rotH) = CoordinateMapper.rotatePoint(
            x = 100.0f,
            y = 200.0f,
            w = 1920,
            h = 1080,
            rotation = 90
        )
        // 90 deg clockwise: x' = h - y = 1080 - 200 = 880, y' = x = 100
        assertEquals(880.0f, xRot, 0.01f)
        assertEquals(100.0f, yRot, 0.01f)
        assertEquals(1080.0f, rotW, 0.01f)
        assertEquals(1920.0f, rotH, 0.01f)
    }

    @Test
    fun testFillCenterMappingPreservesCenter() {
        val mapper = CoordinateMapper(
            frameWidth = 1920,
            frameHeight = 1080,
            viewWidth = 1080,
            viewHeight = 2400,
            rotationDegrees = 0
        )
        // Camera frame center (960, 540) must map exactly to screen center (540, 1200)
        val screenPt = mapper.mapFramePointToScreen(960.0f, 540.0f)
        assertEquals(540.0f, screenPt.x, 1.0f)
        assertEquals(1200.0f, screenPt.y, 1.0f)
    }
}
