package com.birdpath.app.ui

import android.content.Context
import android.graphics.*
import android.util.AttributeSet
import android.view.View
import kotlin.math.max
import kotlin.math.min

/**
 * OverlayView
 * Renders Layers 2 and 3 on top of the CameraX PreviewView:
 * - Layer 2: Bounding boxes with Track ID, confidence, distinct color per ID
 * - Layer 3: Catmull-Rom spline smoothed trajectory curve, fading alpha (1 - i/K),
 *   shrinking line width, and widening uncertainty confidence band.
 * - Supports graceful 500ms fading for lost tracks.
 */
class OverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    data class TrackRenderData(
        val trackId: Int,
        val boxRect: RectF,
        val confidence: Float,
        val predictedPoints: List<Point2D>,
        val uncertaintyRadii: List<Float>,
        val isLost: Boolean = false,
        val lostSinceMs: Long = 0L
    )

    private val activeTracks = mutableListOf<TrackRenderData>()

    var showLayer2Boxes: Boolean = true
    var showLayer3Trajectory: Boolean = true

    // Paint configurations
    private val boxPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 5.0f
    }

    private val textBgPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        color = Color.argb(180, 0, 0, 0)
    }

    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 34.0f
        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
    }

    private val pathPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }

    private val bandPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }

    // Color palette for distinct bird IDs
    private val idColors = intArrayOf(
        Color.parseColor("#00E676"), // Neon Green
        Color.parseColor("#00E5FF"), // Cyan
        Color.parseColor("#FFD600"), // Yellow
        Color.parseColor("#FF4081"), // Pink
        Color.parseColor("#7C4DFF"), // Deep Purple
        Color.parseColor("#FF6D00"), // Orange
        Color.parseColor("#1DE9B6")  // Teal
    )

    fun updateTracks(tracks: List<TrackRenderData>) {
        post {
            activeTracks.clear()
            activeTracks.addAll(tracks)
            invalidate()
        }
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val now = System.currentTimeMillis()

        for (track in activeTracks) {
            val baseColor = idColors[track.trackId % idColors.size]

            // Calculate fade factor if lost (up to 500ms fadeout)
            var alphaMultiplier = 1.0f
            if (track.isLost) {
                val elapsed = now - track.lostSinceMs
                if (elapsed > 500L) continue
                alphaMultiplier = 1.0f - (elapsed / 500.0f)
            }

            // --- Layer 2: Bounding Box & Label ---
            if (showLayer2Boxes) {
                drawBoundingBox(canvas, track, baseColor, alphaMultiplier)
            }

            // --- Layer 3: Predicted Flight Path & Uncertainty Band ---
            if (showLayer3Trajectory && track.predictedPoints.isNotEmpty()) {
                drawTrajectoryAndBand(canvas, track, baseColor, alphaMultiplier)
            }
        }
    }

    private fun drawBoundingBox(
        canvas: Canvas,
        track: TrackRenderData,
        color: Int,
        alphaMultiplier: Float
    ) {
        val alpha = (255 * alphaMultiplier).toInt().coerceIn(0, 255)
        boxPaint.color = color
        boxPaint.alpha = alpha

        canvas.drawRoundRect(track.boxRect, 8f, 8f, boxPaint)

        // Text label: "ID: #2 (87%)"
        val label = if (track.isLost) {
            "ID #${track.trackId} [LOST]"
        } else {
            "ID #${track.trackId} (${(track.confidence * 100).toInt()}%)"
        }

        val textWidth = textPaint.measureText(label)
        val textHeight = 36.0f
        val bgRect = RectF(
            track.boxRect.left,
            track.boxRect.top - textHeight - 8f,
            track.boxRect.left + textWidth + 16f,
            track.boxRect.top
        )

        textBgPaint.alpha = (180 * alphaMultiplier).toInt().coerceIn(0, 180)
        textPaint.alpha = alpha
        canvas.drawRoundRect(bgRect, 4f, 4f, textBgPaint)
        canvas.drawText(label, bgRect.left + 8f, bgRect.bottom - 8f, textPaint)
    }

    private fun drawTrajectoryAndBand(
        canvas: Canvas,
        track: TrackRenderData,
        color: Int,
        alphaMultiplier: Float
    ) {
        val points = track.predictedPoints
        val radii = track.uncertaintyRadii
        val k = points.size.toFloat()

        // 1. Draw uncertainty band: widening translucent ellipses / circles
        for (i in points.indices) {
            val pt = points[i]
            val r = if (i < radii.size) radii[i] else (i * 3.0f + 6.0f)
            val bandAlpha = ((0.35f * (1.0f - i / k)) * 255 * alphaMultiplier).toInt().coerceIn(0, 255)

            bandPaint.color = color
            bandPaint.alpha = bandAlpha
            canvas.drawCircle(pt.x, pt.y, r, bandPaint)
        }

        // 2. Draw smoothed Catmull-Rom spline segments with shrinking stroke width & fading alpha
        if (points.size >= 2) {
            for (i in 0 until points.size - 1) {
                val p1 = points[i]
                val p2 = points[i + 1]

                val progress = i / k
                val segAlpha = ((1.0f - progress) * 255 * alphaMultiplier).toInt().coerceIn(0, 255)
                val strokeW = max(2.5f, 9.0f * (1.0f - progress * 0.7f))

                pathPaint.color = color
                pathPaint.alpha = segAlpha
                pathPaint.strokeWidth = strokeW

                canvas.drawLine(p1.x, p1.y, p2.x, p2.y, pathPaint)
            }
        }
    }
}
