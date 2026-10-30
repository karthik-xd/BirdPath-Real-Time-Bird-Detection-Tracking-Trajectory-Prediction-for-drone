package com.birdpath.app.storage

import android.content.Context
import android.content.SharedPreferences

/**
 * SettingsManager
 * Manages user preferences for inference threshold, prediction horizon,
 * tiling, camera motion compensation, and multi-layer rendering toggles.
 */
class SettingsManager(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("bird_path_prefs", Context.MODE_PRIVATE)

    var confidenceThreshold: Float
        get() = prefs.getFloat(KEY_CONF_THRESH, 0.25f)
        set(value) = prefs.edit().putFloat(KEY_CONF_THRESH, value).apply()

    var predictionHorizon: Int
        get() = prefs.getInt(KEY_HORIZON, 20)
        set(value) = prefs.edit().putInt(KEY_HORIZON, value).apply()

    var isTiledInferenceEnabled: Boolean
        get() = prefs.getBoolean(KEY_TILED_INFERENCE, false)
        set(value) = prefs.edit().putBoolean(KEY_TILED_INFERENCE, value).apply()

    var isCameraCompensationEnabled: Boolean
        get() = prefs.getBoolean(KEY_CAM_COMPENSATION, true)
        set(value) = prefs.edit().putBoolean(KEY_CAM_COMPENSATION, value).apply()

    var showLayer1Preview: Boolean
        get() = prefs.getBoolean(KEY_LAYER_1, true)
        set(value) = prefs.edit().putBoolean(KEY_LAYER_1, value).apply()

    var showLayer2Boxes: Boolean
        get() = prefs.getBoolean(KEY_LAYER_2, true)
        set(value) = prefs.edit().putBoolean(KEY_LAYER_2, value).apply()

    var showLayer3Path: Boolean
        get() = prefs.getBoolean(KEY_LAYER_3, true)
        set(value) = prefs.edit().putBoolean(KEY_LAYER_3, value).apply()

    companion object {
        private const val KEY_CONF_THRESH = "conf_threshold"
        private const val KEY_HORIZON = "prediction_horizon"
        private const val KEY_TILED_INFERENCE = "tiled_inference"
        private const val KEY_CAM_COMPENSATION = "cam_compensation"
        private const val KEY_LAYER_1 = "layer_1_preview"
        private const val KEY_LAYER_2 = "layer_2_boxes"
        private const val KEY_LAYER_3 = "layer_3_path"
    }
}
