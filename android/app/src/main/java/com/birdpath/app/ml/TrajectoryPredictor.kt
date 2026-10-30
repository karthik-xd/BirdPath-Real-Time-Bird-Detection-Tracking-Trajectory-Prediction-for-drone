package com.birdpath.app.ml

import android.content.Context
import android.graphics.PointF
import com.birdpath.app.ui.Point2D
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.channels.FileChannel
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.sqrt

/**
 * TrajectoryPredictor
 * Runs 2-layer GRU TFLite model to forecast next K flight coordinates
 * with Gaussian uncertainty variance.
 */
class TrajectoryPredictor(
    private val context: Context,
    private val modelFileName: String = "bird_trajectory_fp16.tflite"
) {
    private var interpreter: Interpreter? = null

    data class PredictionResult(
        val futurePoints: List<Point2D>,
        val uncertaintyRadii: List<Float>
    )

    init {
        try {
            val options = Interpreter.Options().apply { setNumThreads(2) }
            val buffer = loadModelFile(modelFileName)
            interpreter = Interpreter(buffer, options)
        } catch (e: Exception) {
            interpreter = null // Fallback to Kalman prediction
        }
    }

    private fun loadModelFile(name: String): ByteBuffer {
        val assetFd = context.assets.openFd(name)
        val fileInputStream = FileInputStream(assetFd.fileDescriptor)
        val fileChannel = fileInputStream.channel
        return fileChannel.map(
            FileChannel.MapMode.READ_ONLY,
            assetFd.startOffset,
            assetFd.declaredLength
        )
    }

    /**
     * Predicts future path given track's history buffer [cx, cy, w, h].
     * If history < 15, falls back to constant velocity extrapolation or pads initial step.
     */
    fun predictTrajectory(
        track: Track,
        frameW: Float,
        frameH: Float,
        horizon: Int = 20
    ): PredictionResult {
        val histList = track.history.toList()
        if (histList.isEmpty()) {
            return PredictionResult(emptyList(), emptyList())
        }

        // If TFLite model is not loaded or history is very short (< 5 frames), use Kalman fallback
        val interp = interpreter
        if (interp == null || histList.size < 5) {
            return predictWithKalmanVelocity(track, horizon)
        }

        // Prepare 15-frame history window [cx, cy, w, h, dx, dy] normalized to [0, 1]
        val paddedHistory = mutableListOf<FloatArray>()
        if (histList.size < 15) {
            val padCount = 15 - histList.size
            for (i in 0 until padCount) {
                paddedHistory.add(histList.first())
            }
            paddedHistory.addAll(histList)
        } else {
            paddedHistory.addAll(histList.takeLast(15))
        }

        // Build (1, 15, 6) float buffer
        val inputBuffer = ByteBuffer.allocateDirect(1 * 15 * 6 * 4).apply {
            order(ByteOrder.nativeOrder())
        }

        for (i in 0 until 15) {
            val b = paddedHistory[i]
            val normCx = b[0] / frameW
            val normCy = b[1] / frameH
            val normW = b[2] / frameW
            val normH = b[3] / frameH

            val prevB = if (i > 0) paddedHistory[i - 1] else b
            val dx = (b[0] - prevB[0]) / frameW
            val dy = (b[1] - prevB[1]) / frameH

            inputBuffer.putFloat(normCx)
            inputBuffer.putFloat(normCy)
            inputBuffer.putFloat(normW)
            inputBuffer.putFloat(normH)
            inputBuffer.putFloat(dx)
            inputBuffer.putFloat(dy)
        }

        // Output buffer: (1, 20, 4) -> [mean_dx, mean_dy, logvar_dx, logvar_dy]
        val outputArray = Array(1) { Array(20) { FloatArray(4) } }
        interp.run(inputBuffer, outputArray)

        val lastCenter = histList.last()
        val lastCx = lastCenter[0]
        val lastCy = lastCenter[1]

        val futurePoints = mutableListOf<Point2D>()
        val radii = mutableListOf<Float>()

        val steps = horizon.coerceIn(5, 20)
        for (k in 0 until steps) {
            val offXNorm = outputArray[0][k][0]
            val offYNorm = outputArray[0][k][1]
            val logVarX = outputArray[0][k][2]
            val logVarY = outputArray[0][k][3]

            val px = lastCx + offXNorm * frameW
            val py = lastCy + offYNorm * frameH
            futurePoints.add(Point2D(px, py))

            // Uncertainty standard deviation mapped to screen radius
            val stdX = sqrt(exp(logVarX.coerceIn(-8f, 4f))) * frameW
            val stdY = sqrt(exp(logVarY.coerceIn(-8f, 4f))) * frameH
            val radius = max(6.0f, (stdX + stdY) * 0.5f)
            radii.add(radius)
        }

        return PredictionResult(futurePoints, radii)
    }

    /**
     * Kinematic Kalman velocity baseline extrapolation.
     */
    private fun predictWithKalmanVelocity(track: Track, horizon: Int): PredictionResult {
        val lastBox = track.getBox()
        val vel = track.kalman.getVelocity()
        val vx = vel[0]
        val vy = vel[1]

        val pts = mutableListOf<Point2D>()
        val radii = mutableListOf<Float>()

        for (k in 1..horizon) {
            val px = lastBox[0] + vx * k
            val py = lastBox[1] + vy * k
            pts.add(Point2D(px, py))
            radii.add(8.0f + k * 1.5f) // Linear uncertainty growth
        }
        return PredictionResult(pts, radii)
    }

    fun close() {
        interpreter?.close()
    }
}
