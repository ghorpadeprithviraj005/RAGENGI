package com.example.ragengi.data.repository

import com.example.ragengi.data.model.CleanupResponse
import com.example.ragengi.data.model.CleanupRunRequest
import com.example.ragengi.data.model.DeleteDocumentResponse
import com.example.ragengi.data.model.EligibleDocumentsResponse
import com.example.ragengi.data.model.IngestionResponse
import com.example.ragengi.data.model.QARequest
import com.example.ragengi.data.model.QAResponse
import com.example.ragengi.data.model.TouchDocumentResponse
import com.example.ragengi.data.remote.RagApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class RagRepository(private val api: RagApi) {

    suspend fun askQuestion(query: String, activeFilename: String? = null): Result<QAResponse> = withContext(Dispatchers.IO) {
        try {
            val response = api.askQuestion(QARequest(query = query, activeFilename = activeFilename))
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun ingestDocument(filePath: String): Result<IngestionResponse> = withContext(Dispatchers.IO) {
        try {
            val file = File(filePath)
            val requestFile = file.asRequestBody("application/pdf".toMediaTypeOrNull())
            val body = MultipartBody.Part.createFormData("file", file.name, requestFile)
            
            val response = api.ingestDocument(body)
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getEligibleDocuments(days: Int = 30, simulatedNow: String? = null): Result<EligibleDocumentsResponse> = withContext(Dispatchers.IO) {
        try {
            val response = api.getEligibleDocuments(days = days, simulatedNow = simulatedNow)
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun runCleanup(days: Int = 30, simulatedNow: String? = null, dryRun: Boolean = false): Result<CleanupResponse> = withContext(Dispatchers.IO) {
        try {
            val response = api.runCleanup(CleanupRunRequest(days = days, simulated_now = simulatedNow, dry_run = dryRun))
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun deleteDocument(filename: String): Result<DeleteDocumentResponse> = withContext(Dispatchers.IO) {
        try {
            val response = api.deleteDocument(filename = filename)
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun touchDocument(filename: String): Result<TouchDocumentResponse> = withContext(Dispatchers.IO) {
        try {
            val response = api.touchDocument(filename = filename)
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
