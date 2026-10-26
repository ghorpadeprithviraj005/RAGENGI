package com.example.ragengi.data.remote

import com.example.ragengi.data.model.CleanupResponse
import com.example.ragengi.data.model.CleanupRunRequest
import com.example.ragengi.data.model.DeleteDocumentResponse
import com.example.ragengi.data.model.EligibleDocumentsResponse
import com.example.ragengi.data.model.IngestionResponse
import com.example.ragengi.data.model.QARequest
import com.example.ragengi.data.model.QAResponse
import com.example.ragengi.data.model.TouchDocumentResponse
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface RagApi {
    @Multipart
    @POST("/api/v1/rag/ingest")
    suspend fun ingestDocument(
        @Part file: MultipartBody.Part
    ): IngestionResponse

    @POST("/api/v1/rag/ask")
    suspend fun askQuestion(@Body request: QARequest): QAResponse

    @GET("/api/v1/rag/cleanup/eligible")
    suspend fun getEligibleDocuments(
        @Query("days") days: Int = 30,
        @Query("simulated_now") simulatedNow: String? = null
    ): EligibleDocumentsResponse

    @POST("/api/v1/rag/cleanup/run")
    suspend fun runCleanup(
        @Body request: CleanupRunRequest = CleanupRunRequest(),
        @Header("X-API-Key") apiKey: String = "ragengi-secure-cleanup-key"
    ): CleanupResponse

    @DELETE("/api/v1/rag/documents/{filename}")
    suspend fun deleteDocument(
        @Path("filename") filename: String,
        @Header("X-API-Key") apiKey: String = "ragengi-secure-cleanup-key"
    ): DeleteDocumentResponse

    @POST("/api/v1/rag/documents/{filename}/touch")
    suspend fun touchDocument(
        @Path("filename") filename: String
    ): TouchDocumentResponse
}
