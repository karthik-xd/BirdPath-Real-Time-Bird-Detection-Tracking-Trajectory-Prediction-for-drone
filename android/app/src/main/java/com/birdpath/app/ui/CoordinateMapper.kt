package com.birdpath.app.ui

import android.graphics.PointF
import android.graphics.RectF
import kotlin.math.max
import kotlin.math.min

/**
 * Pure 2D point representation for mathematical projection decoupled from Android UI stubs.
 */
data class Point2D(val x: Float, val y: Float) {
    fun toPointF(): PointF = PointF(x, y)
}

/**
 * CoordinateMapper
 * Maps coordinates from YOLO 640x640 letterboxed model space into
 * the device's screen View space, correctly handling:
 * 1. Aspect ratio letterboxing padding (padX, padY, scale)
 * 2. Sensor orientation rotation (0, 90, 180, 270 degrees)
 * 3. CameraX PreviewView FILL_CENTER scaling and symmetrical cropping
 */
class CoordinateMapper(
    var frameWidth: Int = 1920,
    var frameHeight: Int = 1080,
    var modelInputWidth: Int = 640,
    var modelInputHeight: Int = 640,
    var viewWidth: Int = 1080,
    var viewHeight: Int = 2400,
    var rotationDegrees: Int = 90
) {

    /**
     * Un-letterboxes a box [cx, cy, w, h] from 640x640 model space back into raw frame space.
     */
    fun unletterboxBox(
        cxModel: Float,
        cyModel: Float,
        wModel: Float,
        hModel: Float
    ): FloatArray {
        val scale = min(
            modelInputWidth.toFloat() / frameWidth,
            modelInputHeight.toFloat() / frameHeight
        )
        val padX = (modelInputWidth - frameWidth * scale) / 2.0f
        val padY = (modelInputHeight - frameHeight * scale) / 2.0f

        val cxFrame = (cxModel - padX) / scale
        val cyFrame = (cyModel - padY) / scale
        val wFrame = wModel / scale
        val hFrame = hModel / scale

        return floatArrayOf(cxFrame, cyFrame, wFrame, hFrame)
    }

    /**
     * Maps a 2D point (xFrame, yFrame) in camera frame space to rotated screen space
     * using CameraX PreviewView FILL_CENTER logic.
     */
    fun mapFramePointToScreen(xFrame: Float, yFrame: Float): Point2D {
        // Step 1: Rotate point according to sensor orientation
        val (xRot, yRot, rotW, rotH) = rotatePoint(xFrame, yFrame, frameWidth, frameHeight, rotationDegrees)

        // Step 2: CameraX FILL_CENTER scaling
        val scale = max(
            viewWidth.toFloat() / rotW,
            viewHeight.toFloat() / rotH
        )
        val scaledW = rotW * scale
        val scaledH = rotH * scale
        val offsetX = (scaledW - viewWidth) / 2.0f
        val offsetY = (scaledH - viewHeight) / 2.0f

        val screenX = xRot * scale - offsetX
        val screenY = yRot * scale - offsetY
        return Point2D(screenX, screenY)
    }

    /**
     * Maps a bounding box [cx, cy, w, h] directly from model space to screen RectF.
     */
    fun mapModelBoxToScreen(
        cxModel: Float,
        cyModel: Float,
        wModel: Float,
        hModel: Float
    ): RectF {
        val (cxFrame, cyFrame, wFrame, hFrame) = unletterboxBox(cxModel, cyModel, wModel, hModel)

        val topLeft = mapFramePointToScreen(cxFrame - wFrame / 2.0f, cyFrame - hFrame / 2.0f)
        val bottomRight = mapFramePointToScreen(cxFrame + wFrame / 2.0f, cyFrame + hFrame / 2.0f)

        return RectF(
            min(topLeft.x, bottomRight.x),
            min(topLeft.y, bottomRight.y),
            max(topLeft.x, bottomRight.x),
            max(topLeft.y, bottomRight.y)
        )
    }

    companion object {
        fun rotatePoint(
            x: Float,
            y: Float,
            w: Int,
            h: Int,
            rotation: Int
        ): FloatArray {
            return when (rotation) {
                90 -> floatArrayOf(h - y, x, h.toFloat(), w.toFloat())
                180 -> floatArrayOf(w - x, h - y, w.toFloat(), h.toFloat())
                270 -> floatArrayOf(y, w - x, h.toFloat(), w.toFloat())
                else -> floatArrayOf(x, y, w.toFloat(), h.toFloat())
            }
        }
    }
}
