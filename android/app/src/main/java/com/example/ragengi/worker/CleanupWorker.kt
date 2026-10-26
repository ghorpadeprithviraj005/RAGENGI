package com.example.ragengi.worker

import android.content.Context
import android.util.Log
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.example.ragengi.data.remote.RagApi
import com.example.ragengi.data.repository.RagRepository
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

class CleanupWorker(
    private val appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    companion object {
        const val TAG = "CleanupWorker"
        const val WORK_NAME = "ragengi_daily_cleanup"
        const val PREFS_NAME = "ragengi_prefs"
        const val KEY_AUTO_CLEANUP_ENABLED = "auto_cleanup_enabled"
        const val KEY_CLEANUP_INACTIVITY_DAYS = "cleanup_inactivity_days"

        fun scheduleDaily(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val workRequest = PeriodicWorkRequestBuilder<CleanupWorker>(24, TimeUnit.HOURS)
                .setConstraints(constraints)
                .build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                workRequest
            )
            Log.d(TAG, "Scheduled daily 30-day cleanup background worker.")
        }

        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
            Log.d(TAG, "Cancelled 30-day cleanup background worker.")
        }
    }

    override suspend fun doWork(): Result {
        val prefs = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val isEnabled = prefs.getBoolean(KEY_AUTO_CLEANUP_ENABLED, false)

        if (!isEnabled) {
            Log.d(TAG, "Auto-cleanup is disabled by user policy. Skipping execution.")
            return Result.success()
        }

        val days = prefs.getInt(KEY_CLEANUP_INACTIVITY_DAYS, 30)
        Log.i(TAG, "Starting periodic inactive document cleanup (threshold: $days days)...")

        return try {
            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(120, TimeUnit.SECONDS)
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl("http://10.0.2.2:8000/")
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()

            val api = retrofit.create(RagApi::class.java)
            val repository = RagRepository(api)

            val result = repository.runCleanup(days = days)
            if (result.isSuccess) {
                val cleanupResponse = result.getOrNull()
                Log.i(
                    TAG,
                    "Cleanup completed successfully. Removed ${cleanupResponse?.deleted_documents?.size ?: 0} documents, ${cleanupResponse?.total_vectors_removed ?: 0} vectors, freed ${cleanupResponse?.freed_bytes ?: 0} bytes."
                )
                Result.success()
            } else {
                val err = result.exceptionOrNull()
                Log.w(TAG, "Cleanup failed with error: ${err?.message}. Will retry on next schedule.", err)
                Result.retry()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Unexpected error in CleanupWorker: ${e.message}", e)
            Result.retry()
        }
    }
}
