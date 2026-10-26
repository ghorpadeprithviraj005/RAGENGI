package com.example.ragengi.data.local

import android.app.ActivityManager
import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.io.File

class StorageManager(private val context: Context) {

    private val modelDir = File(context.filesDir, "models")
    private val faissDir = File(context.filesDir, "faiss")

    init {
        if (!modelDir.exists()) modelDir.mkdirs()
        if (!faissDir.exists()) faissDir.mkdirs()
    }

    /**
     * Checks if the required models are present in the app's internal storage.
     */
    fun areModelsInstalled(): Boolean {
        val ggufModel = File(modelDir, "llama-2-7b.gguf")
        val onnxModel = File(modelDir, "all-MiniLM-L6-v2.onnx")
        val faissIndex = File(faissDir, "vector_store.index")
        
        // For a real implementation, we check if they exist.
        // Returning false here triggers the setup wizard.
        return ggufModel.exists() && onnxModel.exists() && faissIndex.exists()
    }

    /**
     * Simulates downloading or copying the models into the internal storage.
     */
    suspend fun setupModels(onProgress: (Int, String) -> Unit): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            // Check RAM before installing massive models
            val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
            val memoryInfo = ActivityManager.MemoryInfo()
            activityManager.getMemoryInfo(memoryInfo)
            
            val totalRamGb = memoryInfo.totalMem / (1024 * 1024 * 1024.0)
            if (totalRamGb < 4.0) {
                return@withContext Result.failure(Exception("Insufficient RAM. Minimum 4GB required for local GGUF models."))
            }

            // Mocking the download/copy process for the GGUF, ONNX, and FAISS files
            onProgress(10, "Preparing to download LLM (GGUF)...")
            delay(1000)
            
            onProgress(40, "Downloading Embedding Model (ONNX)...")
            delay(1000)
            
            onProgress(70, "Downloading FAISS Index...")
            delay(1000)
            
            onProgress(90, "Optimizing storage & mapping memory...")
            delay(1000)

            // Simulate file creation to pass `areModelsInstalled()` next time
            File(modelDir, "llama-2-7b.gguf").createNewFile()
            File(modelDir, "all-MiniLM-L6-v2.onnx").createNewFile()
            File(faissDir, "vector_store.index").createNewFile()
            
            onProgress(100, "Setup Complete!")
            Result.success(Unit)
        } catch (e: Exception) {
            Log.e("StorageManager", "Setup failed", e)
            Result.failure(e)
        }
    }
}
