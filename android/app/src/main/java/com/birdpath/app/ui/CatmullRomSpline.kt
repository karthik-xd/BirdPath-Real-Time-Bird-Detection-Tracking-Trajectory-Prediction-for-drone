package com.birdpath.app.ui

import android.graphics.Path

/**
 * CatmullRomSpline
 * Generates smooth C1-continuous cubic splines across trajectory prediction points
 * to eliminate visual jitter during high-speed flight rendering.
 */
object CatmullRomSpline {

    /**
     * Interpolates between p1 and p2 using p0 and p3 as control points with parameter t in [0, 1].
     */
    fun interpolatePoint(
        p0: Point2D,
        p1: Point2D,
        p2: Point2D,
        p3: Point2D,
        t: Float
    ): Point2D {
        val t2 = t * t
        val t3 = t2 * t

        val x = 0.5f * (
            (2.0f * p1.x) +
            (-p0.x + p2.x) * t +
            (2.0f * p0.x - 5.0f * p1.x + 4.0f * p2.x - p3.x) * t2 +
            (-p0.x + 3.0f * p1.x - 3.0f * p2.x + p3.x) * t3
        )

        val y = 0.5f * (
            (2.0f * p1.y) +
            (-p0.y + p2.y) * t +
            (2.0f * p0.y - 5.0f * p1.y + 4.0f * p2.y - p3.y) * t2 +
            (-p0.y + 3.0f * p1.y - 3.0f * p2.y + p3.y) * t3
        )

        return Point2D(x, y)
    }

    /**
     * Creates a smooth Android Path given a list of trajectory points.
     */
    fun createSplinePath(points: List<Point2D>, subdivisionsPerSegment: Int = 6): Path {
        val path = Path()
        if (points.isEmpty()) return path
        if (points.size < 3) {
            path.moveTo(points.first().x, points.first().y)
            for (i in 1 until points.size) {
                path.lineTo(points[i].x, points[i].y)
            }
            return path
        }

        path.moveTo(points.first().x, points.first().y)

        for (i in 0 until points.size - 1) {
            val p0 = if (i == 0) points[i] else points[i - 1]
            val p1 = points[i]
            val p2 = points[i + 1]
            val p3 = if (i + 2 < points.size) points[i + 2] else p2

            for (s in 1..subdivisionsPerSegment) {
                val t = s.toFloat() / subdivisionsPerSegment
                val pt = interpolatePoint(p0, p1, p2, p3, t)
                path.lineTo(pt.x, pt.y)
            }
        }

        return path
    }
}
