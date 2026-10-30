package com.birdpath.app.ml

/**
 * KalmanFilter
 * 8-state linear Kalman filter tracking bounding box position and velocity:
 * x = [cx, cy, w, h, vx, vy, vw, vh]^T
 */
class KalmanFilter(
    initBox: FloatArray, // [cx, cy, w, h]
    val dt: Float = 1.0f
) {
    // State vector (8x1)
    val x = FloatArray(8)

    // State covariance matrix P (8x8)
    val P = Array(8) { FloatArray(8) }

    // State transition matrix F (8x8)
    private val F = Array(8) { FloatArray(8) }

    // Process noise covariance Q (8x8)
    private val Q = Array(8) { FloatArray(8) }

    // Measurement noise covariance R (4x4)
    private val R = Array(4) { FloatArray(4) }

    init {
        for (i in 0..3) {
            x[i] = initBox[i]
            x[i + 4] = 0.0f // initial velocity
        }

        // Initialize F: x_pos += dt * v
        for (i in 0..7) F[i][i] = 1.0f
        for (i in 0..3) F[i][i + 4] = dt

        // Initialize P: high uncertainty for unobserved velocities
        for (i in 0..3) P[i][i] = 10.0f
        for (i in 4..7) P[i][i] = 100.0f

        // Initialize Q: process noise
        for (i in 0..3) Q[i][i] = 1.0f
        for (i in 4..7) Q[i][i] = 4.0f

        // Initialize R: measurement noise
        for (i in 0..3) R[i][i] = 2.0f
    }

    /**
     * Prediction step:
     * x = F * x
     * P = F * P * F^T + Q
     */
    fun predict(): FloatArray {
        // x = F * x
        val newX = FloatArray(8)
        for (i in 0..7) {
            var sum = 0.0f
            for (j in 0..7) {
                sum += F[i][j] * x[j]
            }
            newX[i] = sum
        }
        System.arraycopy(newX, 0, x, 0, 8)

        // FP = F * P
        val FP = Array(8) { FloatArray(8) }
        for (i in 0..7) {
            for (j in 0..7) {
                var s = 0.0f
                for (k in 0..7) s += F[i][k] * P[k][j]
                FP[i][j] = s
            }
        }

        // P = FP * F^T + Q
        for (i in 0..7) {
            for (j in 0..7) {
                var s = 0.0f
                for (k in 0..7) s += FP[i][k] * F[j][k] // F^T[k][j] == F[j][k]
                P[i][j] = s + Q[i][j]
            }
        }

        return floatArrayOf(x[0], x[1], x[2], x[3])
    }

    /**
     * Update step:
     * y = z - H * x  (H maps state indices 0..3)
     * S = H * P * H^T + R
     * K = P * H^T * S^-1
     * x = x + K * y
     * P = (I - K * H) * P
     */
    fun update(z: FloatArray) {
        // Residual y = z - H * x
        val y = FloatArray(4)
        for (i in 0..3) {
            y[i] = z[i] - x[i]
        }

        // S = P[0..3][0..3] + R (since H is [I_4, 0_4])
        val S = Array(4) { FloatArray(4) }
        for (i in 0..3) {
            for (j in 0..3) {
                S[i][j] = P[i][j] + R[i][j]
            }
        }

        // Invert 4x4 matrix S
        val SInv = invert4x4(S)

        // K = P * H^T * S^-1 (8x4 matrix)
        // P * H^T is the first 4 columns of P (8x4)
        val K = Array(8) { FloatArray(4) }
        for (i in 0..7) {
            for (j in 0..3) {
                var s = 0.0f
                for (k in 0..3) {
                    s += P[i][k] * SInv[k][j]
                }
                K[i][j] = s
            }
        }

        // x = x + K * y
        for (i in 0..7) {
            var sum = 0.0f
            for (j in 0..3) {
                sum += K[i][j] * y[j]
            }
            x[i] += sum
        }

        // P = (I - K * H) * P
        // KH is 8x8 where cols 0..3 are K[i][j] and cols 4..7 are 0
        val I_KH = Array(8) { FloatArray(8) }
        for (i in 0..7) {
            for (j in 0..7) {
                val kh = if (j < 4) K[i][j] else 0.0f
                val eye = if (i == j) 1.0f else 0.0f
                I_KH[i][j] = eye - kh
            }
        }

        val newP = Array(8) { FloatArray(8) }
        for (i in 0..7) {
            for (j in 0..7) {
                var s = 0.0f
                for (k in 0..7) s += I_KH[i][k] * P[k][j]
                newP[i][j] = s
            }
        }
        for (i in 0..7) {
            System.arraycopy(newP[i], 0, P[i], 0, 8)
        }
    }

    fun getBox(): FloatArray = floatArrayOf(x[0], x[1], x[2], x[3])

    fun getVelocity(): FloatArray = floatArrayOf(x[4], x[5], x[6], x[7])

    companion object {
        /**
         * Analytical 4x4 matrix inversion using cofactor expansion.
         */
        fun invert4x4(m: Array<FloatArray>): Array<FloatArray> {
            val inv = Array(4) { FloatArray(4) }
            val a = FloatArray(16)
            for (i in 0..3) for (j in 0..3) a[i * 4 + j] = m[i][j]

            val b = FloatArray(16)
            b[0] = a[5]*a[10]*a[15] - a[5]*a[11]*a[14] - a[9]*a[6]*a[15] + a[9]*a[7]*a[14] + a[13]*a[6]*a[11] - a[13]*a[7]*a[10]
            b[4] = -a[4]*a[10]*a[15] + a[4]*a[11]*a[14] + a[8]*a[6]*a[15] - a[8]*a[7]*a[14] - a[12]*a[6]*a[11] + a[12]*a[7]*a[10]
            b[8] = a[4]*a[9]*a[15] - a[4]*a[11]*a[13] - a[8]*a[5]*a[15] + a[8]*a[7]*a[13] + a[12]*a[5]*a[11] - a[12]*a[7]*a[9]
            b[12] = -a[4]*a[9]*a[14] + a[4]*a[10]*a[13] + a[8]*a[5]*a[14] - a[8]*a[6]*a[13] - a[12]*a[5]*a[10] + a[12]*a[6]*a[9]

            b[1] = -a[1]*a[10]*a[15] + a[1]*a[11]*a[14] + a[9]*a[2]*a[15] - a[9]*a[3]*a[14] - a[13]*a[2]*a[11] + a[13]*a[3]*a[10]
            b[5] = a[0]*a[10]*a[15] - a[0]*a[11]*a[14] - a[8]*a[2]*a[15] + a[8]*a[3]*a[14] + a[12]*a[2]*a[11] - a[12]*a[3]*a[10]
            b[9] = -a[0]*a[9]*a[15] + a[0]*a[11]*a[13] + a[8]*a[1]*a[15] - a[8]*a[3]*a[13] - a[12]*a[1]*a[11] + a[12]*a[3]*a[9]
            b[13] = a[0]*a[9]*a[14] - a[0]*a[10]*a[13] - a[8]*a[1]*a[14] + a[8]*a[2]*a[13] + a[12]*a[1]*a[10] - a[12]*a[2]*a[9]

            b[2] = a[1]*a[6]*a[15] - a[1]*a[7]*a[14] - a[5]*a[2]*a[15] + a[5]*a[3]*a[14] + a[13]*a[2]*a[7] - a[13]*a[3]*a[6]
            b[6] = -a[0]*a[6]*a[15] + a[0]*a[7]*a[14] + a[4]*a[2]*a[15] - a[4]*a[3]*a[14] - a[12]*a[2]*a[7] + a[12]*a[3]*a[6]
            b[10] = a[0]*a[5]*a[15] - a[0]*a[7]*a[13] - a[4]*a[1]*a[15] + a[4]*a[3]*a[13] + a[12]*a[1]*a[7] - a[12]*a[3]*a[5]
            b[14] = -a[0]*a[5]*a[14] + a[0]*a[6]*a[13] + a[4]*a[1]*a[14] - a[4]*a[2]*a[13] - a[12]*a[1]*a[6] + a[12]*a[2]*a[5]

            b[3] = -a[1]*a[6]*a[11] + a[1]*a[7]*a[10] + a[5]*a[2]*a[11] - a[5]*a[3]*a[10] - a[9]*a[2]*a[7] + a[9]*a[3]*a[6]
            b[7] = a[0]*a[6]*a[11] - a[0]*a[7]*a[10] - a[4]*a[2]*a[11] + a[4]*a[3]*a[10] + a[8]*a[2]*a[7] - a[8]*a[3]*a[6]
            b[11] = -a[0]*a[5]*a[11] + a[0]*a[7]*a[9] + a[4]*a[1]*a[11] - a[4]*a[3]*a[9] - a[8]*a[1]*a[7] + a[8]*a[3]*a[5]
            b[15] = a[0]*a[5]*a[10] - a[0]*a[6]*a[9] - a[4]*a[1]*a[10] + a[4]*a[2]*a[9] + a[8]*a[1]*a[6] - a[8]*a[2]*a[5]

            var det = a[0]*b[0] + a[1]*b[4] + a[2]*b[8] + a[3]*b[12]
            if (det == 0.0f) det = 1e-6f
            val invDet = 1.0f / det

            for (i in 0..3) {
                for (j in 0..3) {
                    inv[i][j] = b[i * 4 + j] * invDet
                }
            }
            return inv
        }
    }
}
