package com.birdpath.app

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.PointF
import android.os.Bundle
import android.util.Size
import android.view.LayoutInflater
import android.view.View
import android.widget.SeekBar
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.birdpath.app.databinding.ActivityMainBinding
import com.birdpath.app.databinding.DialogSettingsBinding
import com.birdpath.app.ml.*
import com.birdpath.app.sensor.CameraMotionCompensator
import com.birdpath.app.sensor.FrameSkipController
import com.birdpath.app.storage.SettingsManager
import com.birdpath.app.storage.TrackRecorder
import com.birdpath.app.ui.CoordinateMapper
import com.birdpath.app.ui.OverlayView
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var settingsManager: SettingsManager
    private lateinit var trackRecorder: TrackRecorder
    private lateinit var cameraMotionCompensator: CameraMotionCompensator
    private lateinit var frameSkipController: FrameSkipController

    private var yoloDetector: YoloDetector? = null
    private var byteTracker = ByteTracker()
    private var trajectoryPredictor: TrajectoryPredictor? = null
    private val coordinateMapper = CoordinateMapper()

    private lateinit var cameraExecutor: ExecutorService

    // Performance tracking
    private var frameCount = 0
    private var lastFpsTimestamp = System.currentTimeMillis()
    private var currentFps = 0.0f

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        settingsManager = SettingsManager(this)
        trackRecorder = TrackRecorder(this)
        cameraMotionCompensator = CameraMotionCompensator(this)
        frameSkipController = FrameSkipController(targetFps = 20.0f)
        cameraExecutor = Executors.newSingleThreadExecutor()

        setupButtons()
        initMlModels()

        if (allPermissionsGranted()) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(
                this, REQUIRED_PERMISSIONS, REQUEST_CODE_PERMISSIONS
            )
        }
    }

    override fun onResume() {
        super.onResume()
        if (settingsManager.isCameraCompensationEnabled) {
            cameraMotionCompensator.start()
        }
    }

    override fun onPause() {
        super.onPause()
        cameraMotionCompensator.stop()
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        yoloDetector?.close()
        trajectoryPredictor?.close()
    }

    private fun initMlModels() {
        cameraExecutor.execute {
            try {
                yoloDetector = YoloDetector(this@MainActivity)
                trajectoryPredictor = TrajectoryPredictor(this@MainActivity)
                runOnUiThread {
                    binding.tvDelegate.text = "Backend: ${yoloDetector?.activeBackend ?: "CPU"}"
                }
            } catch (e: Exception) {
                runOnUiThread {
                    Toast.makeText(this, "Model init fallback to Kalman baseline", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun setupButtons() {
        // Record Button Toggle
        binding.btnRecord.setOnClickListener {
            if (trackRecorder.isRecording()) {
                val exportedFile = trackRecorder.stopRecording()
                binding.btnRecord.text = getString(R.string.btn_record)
                binding.btnRecord.setBackgroundColor(ContextCompat.getColor(this, R.color.recording_red))
                Toast.makeText(this, "Saved track JSON: ${exportedFile?.name}", Toast.LENGTH_LONG).show()
            } else {
                trackRecorder.startRecording()
                binding.btnRecord.text = "STOP"
                binding.btnRecord.setBackgroundColor(ContextCompat.getColor(this, R.color.purple_700))
                Toast.makeText(this, "Track Recording Started", Toast.LENGTH_SHORT).show()
            }
        }

        // Settings Dialog Button
        binding.btnSettings.setOnClickListener {
            showSettingsDialog()
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            // Preview use case
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }

            // ImageAnalysis use case with KEEP_ONLY_LATEST to prevent frame lagging
            val imageAnalysis = ImageAnalysis.Builder()
                .setTargetResolution(Size(1920, 1080))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                .build()

            imageAnalysis.setAnalyzer(cameraExecutor) { imageProxy ->
                processCameraFrame(imageProxy)
            }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageAnalysis)
            } catch (e: Exception) {
                Toast.makeText(this, "Camera binding error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }, ContextCompat.getMainExecutor(this))
    }

    @SuppressLint("UnsafeOptInUsageError")
    private fun processCameraFrame(imageProxy: ImageProxy) {
        val frameW = imageProxy.width
        val frameH = imageProxy.height
        val rotationDegrees = imageProxy.imageInfo.rotationDegrees

        // Update coordinate mapper dimensions
        coordinateMapper.frameWidth = frameW
        coordinateMapper.frameHeight = frameH
        coordinateMapper.rotationDegrees = rotationDegrees
        coordinateMapper.viewWidth = binding.overlayView.width
        coordinateMapper.viewHeight = binding.overlayView.height

        // Calculate real-time FPS
        frameCount++
        val now = System.currentTimeMillis()
        if (now - lastFpsTimestamp >= 1000L) {
            currentFps = frameCount * 1000.0f / (now - lastFpsTimestamp)
            frameCount = 0
            lastFpsTimestamp = now
        }

        // Camera ego-motion compensation
        if (settingsManager.isCameraCompensationEnabled) {
            val (shiftX, shiftY) = cameraMotionCompensator.consumeShift()
            if (shiftX != 0.0f || shiftY != 0.0f) {
                for (trk in byteTracker.tracks) {
                    trk.kalman.x[0] += shiftX
                    trk.kalman.x[1] += shiftY
                }
            }
        }

        // Frame-skipping controller to maintain 20+ FPS
        val detector = yoloDetector
        val lastLatency = detector?.lastInferenceTimeMs ?: 0L
        val shouldDetect = frameSkipController.shouldRunDetector(byteTracker.tracks, lastLatency)

        val detections = mutableListOf<ByteTracker.Detection>()
        if (shouldDetect && detector != null) {
            val bitmap = imageProxy.toBitmap()
            val rawDets = detector.detect(
                bitmap = bitmap,
                confThreshold = settingsManager.confidenceThreshold,
                enableTiling = settingsManager.isTiledInferenceEnabled
            )
            detections.addAll(rawDets)
        }

        // ByteTrack association and Kalman tracking update
        val activeTracks = byteTracker.update(detections)

        // Record tracking session
        trackRecorder.recordFrame(activeTracks, frameW.toFloat(), frameH.toFloat())

        // Build 3-layer rendering data
        val horizon = settingsManager.predictionHorizon
        val renderList = mutableListOf<OverlayView.TrackRenderData>()

        for (trk in activeTracks) {
            val box = trk.getBox()
            // Map box to screen RectF
            val screenRect = coordinateMapper.mapModelBoxToScreen(box[0], box[1], box[2], box[3])

            // Predict trajectory with GRU (or Kalman velocity fallback)
            val pred = trajectoryPredictor?.predictTrajectory(
                track = trk,
                frameW = frameW.toFloat(),
                frameH = frameH.toFloat(),
                horizon = horizon
            )

            val screenPoints = mutableListOf<com.birdpath.app.ui.Point2D>()
            pred?.futurePoints?.forEach { pt ->
                screenPoints.add(coordinateMapper.mapFramePointToScreen(pt.x, pt.y))
            }

            renderList.add(
                OverlayView.TrackRenderData(
                    trackId = trk.id,
                    boxRect = screenRect,
                    confidence = trk.score,
                    predictedPoints = screenPoints,
                    uncertaintyRadii = pred?.uncertaintyRadii ?: emptyList(),
                    isLost = (trk.state == TrackLifecycle.LOST),
                    lostSinceMs = trk.lostSinceMs
                )
            )
        }

        // Update OverlayView on UI thread
        binding.overlayView.showLayer2Boxes = settingsManager.showLayer2Boxes
        binding.overlayView.showLayer3Trajectory = settingsManager.showLayer3Path
        binding.overlayView.updateTracks(renderList)

        // Update Debug Panel
        runOnUiThread {
            binding.tvFps.text = String.format("FPS: %.1f", currentFps)
            binding.tvInferenceLatency.text = "Inference: ${detector?.lastInferenceTimeMs ?: 0} ms"
            binding.tvTracksCount.text = "Active Tracks: ${activeTracks.size}"
            binding.previewView.visibility = if (settingsManager.showLayer1Preview) View.VISIBLE else View.INVISIBLE
        }

        imageProxy.close()
    }

    private fun showSettingsDialog() {
        val dialogBinding = DialogSettingsBinding.inflate(LayoutInflater.from(this))
        val dialog = AlertDialog.Builder(this)
            .setView(dialogBinding.root)
            .create()

        // Sync initial UI values
        val initialConf = (settingsManager.confidenceThreshold * 100).toInt()
        dialogBinding.sbConfidence.progress = initialConf
        dialogBinding.tvConfLabel.text = "Confidence Threshold: ${String.format("%.2f", settingsManager.confidenceThreshold)}"

        val initialHorizon = settingsManager.predictionHorizon
        dialogBinding.sbHorizon.progress = initialHorizon - 5
        dialogBinding.tvHorizonLabel.text = "Prediction Horizon: $initialHorizon points"

        dialogBinding.switchTiled.isChecked = settingsManager.isTiledInferenceEnabled
        dialogBinding.switchCamComp.isChecked = settingsManager.isCameraCompensationEnabled
        dialogBinding.switchLayer1.isChecked = settingsManager.showLayer1Preview
        dialogBinding.switchLayer2.isChecked = settingsManager.showLayer2Boxes
        dialogBinding.switchLayer3.isChecked = settingsManager.showLayer3Path

        // Listeners
        dialogBinding.sbConfidence.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                val conf = progress / 100.0f
                settingsManager.confidenceThreshold = conf
                dialogBinding.tvConfLabel.text = "Confidence Threshold: ${String.format("%.2f", conf)}"
            }
            override fun onStartTrackingTouch(p0: SeekBar?) {}
            override fun onStopTrackingTouch(p0: SeekBar?) {}
        })

        dialogBinding.sbHorizon.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar?, progress: Int, fromUser: Boolean) {
                val h = progress + 5
                settingsManager.predictionHorizon = h
                dialogBinding.tvHorizonLabel.text = "Prediction Horizon: $h points"
            }
            override fun onStartTrackingTouch(p0: SeekBar?) {}
            override fun onStopTrackingTouch(p0: SeekBar?) {}
        })

        dialogBinding.switchTiled.setOnCheckedChangeListener { _, isChecked ->
            settingsManager.isTiledInferenceEnabled = isChecked
        }

        dialogBinding.switchCamComp.setOnCheckedChangeListener { _, isChecked ->
            settingsManager.isCameraCompensationEnabled = isChecked
            if (isChecked) cameraMotionCompensator.start() else cameraMotionCompensator.stop()
        }

        dialogBinding.switchLayer1.setOnCheckedChangeListener { _, isChecked ->
            settingsManager.showLayer1Preview = isChecked
        }
        dialogBinding.switchLayer2.setOnCheckedChangeListener { _, isChecked ->
            settingsManager.showLayer2Boxes = isChecked
        }
        dialogBinding.switchLayer3.setOnCheckedChangeListener { _, isChecked ->
            settingsManager.showLayer3Path = isChecked
        }

        dialogBinding.btnCloseSettings.setOnClickListener {
            dialog.dismiss()
        }

        dialog.show()
    }

    private fun allPermissionsGranted() = REQUIRED_PERMISSIONS.all {
        ContextCompat.checkSelfPermission(baseContext, it) == PackageManager.PERMISSION_GRANTED
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CODE_PERMISSIONS) {
            if (allPermissionsGranted()) {
                startCamera()
            } else {
                Toast.makeText(this, "Camera permissions are required for BirdPath", Toast.LENGTH_SHORT).show()
                finish()
            }
        }
    }

    companion object {
        private const val REQUEST_CODE_PERMISSIONS = 1001
        private val REQUIRED_PERMISSIONS = arrayOf(Manifest.permission.CAMERA)
    }
}
