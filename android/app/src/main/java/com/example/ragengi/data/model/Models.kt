package com.example.ragengi.data.model

data class QARequest(
    val query: String,
    val top_k: Int? = 5,
    @com.google.gson.annotations.SerializedName("active_filename")
    val activeFilename: String? = null
)

data class Citation(
    val chunk_id: Int,
    val page_number: Int
)

data class QAResponse(
    val query: String,
    val answer: String,
    val citations: List<Citation>
)

data class IngestionRequest(
    val file_path: String
)

data class IngestionResponse(
    val file_path: String,
    val total_chunks: Int,
    val status: String
)

data class ChatMessage(
    val id: String = java.util.UUID.randomUUID().toString(),
    val text: String,
    val isUser: Boolean,
    val citations: List<Citation> = emptyList(),
    val isTyping: Boolean = false
)

data class EligibleDocument(
    val filename: String,
    val file_path: String,
    val last_access: String,
    val inactive_days: Double,
    val file_size_bytes: Long,
    val vector_count: Int
)

data class EligibleDocumentsResponse(
    val inactivity_threshold_days: Int,
    val current_time: String,
    val eligible_count: Int,
    val documents: List<EligibleDocument> = emptyList()
)

data class DeleteDocumentResponse(
    val filename: String,
    val deleted_files: List<String> = emptyList(),
    val vectors_removed: Int = 0,
    val status: String = "success"
)

data class CleanupResponse(
    val inactivity_days: Int,
    val deleted_documents: List<String> = emptyList(),
    val total_vectors_removed: Int = 0,
    val freed_bytes: Long = 0,
    val status: String = "success"
)

data class TouchDocumentResponse(
    val filename: String,
    val vectors_updated: Int,
    val last_access: String,
    val status: String = "success"
)

data class CleanupRunRequest(
    val days: Int = 30,
    val simulated_now: String? = null,
    val dry_run: Boolean = false
)
