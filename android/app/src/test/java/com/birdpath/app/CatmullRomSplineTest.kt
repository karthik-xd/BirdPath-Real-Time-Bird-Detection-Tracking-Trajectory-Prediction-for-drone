package com.birdpath.app

import com.birdpath.app.ui.CatmullRomSpline
import com.birdpath.app.ui.Point2D
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CatmullRomSplineTest {

    @Test
    fun testInterpolationEndpoints() {
        val p0 = Point2D(0f, 0f)
        val p1 = Point2D(10f, 10f)
        val p2 = Point2D(20f, 10f)
        val p3 = Point2D(30f, 0f)

        // At t = 0, spline must equal p1 exactly
        val ptStart = CatmullRomSpline.interpolatePoint(p0, p1, p2, p3, 0.0f)
        assertEquals(p1.x, ptStart.x, 1e-4f)
        assertEquals(p1.y, ptStart.y, 1e-4f)

        // At t = 1, spline must equal p2 exactly
        val ptEnd = CatmullRomSpline.interpolatePoint(p0, p1, p2, p3, 1.0f)
        assertEquals(p2.x, ptEnd.x, 1e-4f)
        assertEquals(p2.y, ptEnd.y, 1e-4f)
    }

    @Test
    fun testIntermediatePointSmoothness() {
        val p0 = Point2D(0f, 0f)
        val p1 = Point2D(10f, 0f)
        val p2 = Point2D(20f, 0f)
        val p3 = Point2D(30f, 0f)

        // Collinear points should interpolate smoothly on the line y = 0
        val mid = CatmullRomSpline.interpolatePoint(p0, p1, p2, p3, 0.5f)
        assertEquals(15f, mid.x, 1e-4f)
        assertEquals(0f, mid.y, 1e-4f)
    }
}
