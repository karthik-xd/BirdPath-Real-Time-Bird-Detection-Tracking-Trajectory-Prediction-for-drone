package com.birdpath.app.sensor

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlin.math.tan

/**
 * CameraMotionCompensator
 * Uses Android Hardware Gyroscope to compute phone ego-rotation rate
 * and transforms it into pixel shift (dx, dy) via camera focal geometry.
 * Offsets track histories to isolate bird velocity from camera pan/tilt.
 */
class CameraMotionCompensator(context: Context) : SensorEventListener {

    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val gyroSensor: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)

    var isEnabled: Boolean = true
    private var lastTimestampNs: Long = 0L

    var deltaPixelX: Float = 0.0f
        private set
    var deltaPixelY: Float = 0.0f
        private set

    // Typical phone camera horizontal field of view in radians (~65 degrees)
    var horizontalFovRad: Float = Math.toRadians(65.0).toFloat()

    fun start() {
        gyroSensor?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_FASTEST)
        }
    }

    fun stop() {
        sensorManager.unregisterListener(this)
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (!isEnabled || event == null || event.sensor.type != Sensor.TYPE_GYROSCOPE) return

        if (lastTimestampNs != 0L) {
            val dt = (event.timestamp - lastTimestampNs) * 1.0e-9f // seconds
            val omegaX = event.values[0] // pitch rate (rad/s)
            val omegaY = event.values[1] // yaw rate (rad/s)

            // Angular displacement: dtheta = omega * dt
            val dThetaX = omegaX * dt
            val dThetaY = omegaY * dt

            // Compute equivalent focal length in pixels for a 1920x1080 frame
            val focalPixels = 1920.0f / (2.0f * tan(horizontalFovRad / 2.0f))

            // Camera pan to the right moves image features to the left (-dx)
            deltaPixelX = -dThetaY * focalPixels
            deltaPixelY = dThetaX * focalPixels
        }
        lastTimestampNs = event.timestamp
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    /**
     * Resets accumulated shift after frame compensation is applied.
     */
    fun consumeShift(): Pair<Float, Float> {
        val shift = Pair(deltaPixelX, deltaPixelY)
        deltaPixelX = 0.0f
        deltaPixelY = 0.0f
        return shift
    }
}
