package com.birdpath.app.ml

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Rect
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.gpu.CompatibilityList
import org.tensorflow.lite.gpu.GpuDelegate
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.channels.FileChannel
import kotlin.math.max
import kotlin.math.min

class YoloDetector(
    private val context: Context,
    private val modelFileName: String = "yolov8n_bird.tflite"
) {
    private var interpreter: Interpreter? = null
    private var gpuDelegate: GpuDelegate? = null
    var activeBackend: String = "CPU"
        private set

    val inputSize = 640
    var lastInferenceTimeMs: Long = 0L
        private set

    init {
        initializeInterpreter()
    }

    private fun initializeInterpreter() {
        val options = Interpreter.Options()
        val compatList = CompatibilityList()

        if (compatList.isDelegateSupportedOnThisDevice) {
            try {
                gpuDelegate = GpuDelegate()
                options.addDelegate(gpuDelegate)
                activeBackend = "GPU"
            } catch (e: Exception) {
                options.setNumThreads(4)
                options.setUseNNAPI(true)
                activeBackend = "NNAPI"
            }
        } else {
            options.setNumThreads(4)
            activeBackend = "CPU (4 threads)"
        }

        try {
            val modelBuffer = loadModelFile(modelFileName)
            interpreter = Interpreter(modelBuffer, options)
        } catch (e: Exception) {
            // Fallback to CPU if GPU delegate initialization failed
            val fallbackOptions = Interpreter.Options().apply { setNumThreads(4) }
            val modelBuffer = loadModelFile(modelFileName)
            interpreter = Interpreter(modelBuffer, fallbackOptions)
            activeBackend = "CPU Fallback"
        }
    }

    private fun loadModelFile(modelName: String): ByteBuffer {
        val assetFd = context.assets.openFd(modelName)
        val fileInputStream = FileInputStream(assetFd.fileDescriptor)
        val fileChannel = fileInputStream.channel
        return fileChannel.map(
            FileChannel.MapMode.READ_ONLY,
            assetFd.startOffset,
            assetFd.declaredLength
        )
    }

    /**
     * Runs YOLO inference on the full bitmap (or letterboxed 640x640).
     */
    fun detect(
        bitmap: Bitmap,
        confThreshold: Float = 0.25f,
        iouThreshold: Float = 0.50f,
        enableTiling: Boolean = false
    ): List<ByteTracker.Detection> {
        val startTime = System.currentTimeMillis()

        val detections = if (enableTiling) {
            runTiledInference(bitmap, confThreshold, iouThreshold)
        } else {
            runSingleInference(bitmap, confThreshold, iouThreshold)
        }

        lastInferenceTimeMs = System.currentTimeMillis() - startTime
        return detections
    }

    private fun runSingleInference(
        bitmap: Bitmap,
        confThreshold: Float,
        iouThreshold: Float
    ): List<ByteTracker.Detection> {
        val interp = interpreter ?: return emptyList()

        val letterboxed = letterboxBitmap(bitmap, inputSize, inputSize)
        val inputBuffer = bitmapToByteBuffer(letterboxed)

        // YOLO output tensor: shape is typically (1, 5, 8400) or (1, 8400, 5)
        // [cx, cy, w, h, bird_score]
        val outputBuffer = Array(1) { Array(5) { FloatArray(8400) } }
        interp.run(inputBuffer, outputBuffer)

        val rawDetections = mutableListOf<ByteTracker.Detection>()
        val matrix = outputBuffer[0] // (5, 8400)

        for (col in 0 until 8400) {
            val score = matrix[4][col]
            if (score >= confThreshold) {
                val cx = matrix[0][col]
                val cy = matrix[1][col]
                val w = matrix[2][col]
                val h = matrix[3][col]
                rawDetections.add(ByteTracker.Detection(cx, cy, w, h, score))
            }
        }

        return nms(rawDetections, iouThreshold)
    }

    private fun runTiledInference(
        bitmap: Bitmap,
        confThreshold: Float,
        iouThreshold: Float
    ): List<ByteTracker.Detection> {
        val cropW = bitmap.width / 2
        val cropH = bitmap.height / 2
        val overlap = 0.15f
        val stepX = (cropW * (1.0f - overlap)).toInt()
        val stepY = (cropH * (1.0f - overlap)).toInt()

        val allDetections = mutableListOf<ByteTracker.Detection>()

        val yOffsets = listOf(0, bitmap.height - cropH)
        val xOffsets = listOf(0, bitmap.width - cropW)

        for (oy in yOffsets) {
            for (ox in xOffsets) {
                val crop = Bitmap.createBitmap(bitmap, ox, oy, cropW, cropH)
                val cropDets = runSingleInference(crop, confThreshold, iouThreshold)
                for (d in cropDets) {
                    // Translate local crop coordinates back to full image frame
                    allDetections.add(
                        ByteTracker.Detection(
                            cx = d.cx + ox,
                            cy = d.cy + oy,
                            w = d.w,
                            h = d.h,
                            score = d.score
                        )
                    )
                }
            }
        }

        return nms(allDetections, iouThreshold)
    }

    private fun letterboxBitmap(src: Bitmap, targetW: Int, targetH: Int): Bitmap {
        val out = Bitmap.createBitmap(targetW, targetH, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(out)
        canvas.drawColor(Color.rgb(114, 114, 114)) // YOLO gray pad

        val scale = min(targetW.toFloat() / src.width, targetH.toFloat() / src.height)
        val scaledW = (src.width * scale).toInt()
        val scaledH = (src.height * scale).toInt()
        val dx = (targetW - scaledW) / 2
        val dy = (targetH - scaledH) / 2

        val dstRect = Rect(dx, dy, dx + scaledW, dy + scaledH)
        canvas.drawBitmap(src, null, dstRect, null)
        return out
    }

    private fun bitmapToByteBuffer(bitmap: Bitmap): ByteBuffer {
        val buffer = ByteBuffer.allocateDirect(4 * inputSize * inputSize * 3)
        buffer.order(ByteOrder.nativeOrder())
        val pixels = IntArray(inputSize * inputSize)
        bitmap.getPixels(pixels, 0, inputSize, 0, 0, inputSize, inputSize)

        for (pixel in pixels) {
            val r = ((pixel shr 16) and 0xFF) / 255.0f
            val g = ((pixel shr 8) and 0xFF) / 255.0f
            val b = (pixel and 0xFF) / 255.0f

            buffer.putFloat(r)
            buffer.putFloat(g)
            buffer.putFloat(b)
        }
        return buffer
    }

    private fun nms(
        detections: List<ByteTracker.Detection>,
        iouThreshold: Float
    ): List<ByteTracker.Detection> {
        val sorted = detections.sortedByDescending { it.score }.toMutableList()
        val picked = mutableListOf<ByteTracker.Detection>()

        while (sorted.isNotEmpty()) {
            val best = sorted.removeAt(0)
            picked.add(best)

            val iter = sorted.iterator()
            while (iter.hasNext()) {
                val candidate = iter.next()
                val iou = ByteTracker.calculateIoU(best.toBoxArray(), candidate.toBoxArray())
                if (iou > iouThreshold) {
                    iter.remove()
                }
            }
        }
        return picked
    }

    fun close() {
        interpreter?.close()
        gpuDelegate?.close()
    }
}
