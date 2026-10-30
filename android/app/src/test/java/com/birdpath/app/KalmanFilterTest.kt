package com.birdpath.app

import com.birdpath.app.ml.KalmanFilter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class KalmanFilterTest {

    @Test
    fun testInitializationAndPredict() {
        val initBox = floatArrayOf(200.0f, 150.0f, 50.0f, 40.0f)
        val kf = KalmanFilter(initBox, dt = 1.0f)

        val boxBefore = kf.getBox()
        assertEquals(200.0f, boxBefore[0], 0.001f)
        assertEquals(150.0f, boxBefore[1], 0.001f)

        // Predict step
        val pred = kf.predict()
        assertEquals(200.0f, pred[0], 0.001f)
        assertEquals(150.0f, pred[1], 0.001f)
    }

    @Test
    fun testMeasurementUpdateProducesVelocity() {
        val initBox = floatArrayOf(100.0f, 100.0f, 50.0f, 40.0f)
        val kf = KalmanFilter(initBox, dt = 1.0f)

        // Bird moves to [110, 105, 50, 40]
        kf.predict()
        kf.update(floatArrayOf(110.0f, 105.0f, 50.0f, 40.0f))

        val vel = kf.getVelocity()
        // Velocity along x (vx) and y (vy) should be positive
        assertTrue("Estimated vx should be positive", vel[0] > 0.0f)
        assertTrue("Estimated vy should be positive", vel[1] > 0.0f)
    }

    @Test
    fun testMatrixInvert4x4Identity() {
        val identity = Array(4) { r ->
            FloatArray(4) { c -> if (r == c) 1.0f else 0.0f }
        }
        val inv = KalmanFilter.invert4x4(identity)
        for (i in 0..3) {
            for (j in 0..3) {
                val expected = if (i == j) 1.0f else 0.0f
                assertEquals(expected, inv[i][j], 1e-4f)
            }
        }
    }
}
