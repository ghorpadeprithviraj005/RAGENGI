package com.example.ragengi.ui.viewmodel

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.ragengi.data.local.db.DocumentDao
import com.example.ragengi.data.local.db.DocumentEntity
import com.example.ragengi.data.repository.RagRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File
import java.io.FileOutputStream
import java.util.UUID

enum class UploadStatus {
    IDLE, UPLOADING, SUCCESS, ERROR
}

class KnowledgeBaseViewModel(
    private val repository: RagRepository,
    private val documentDao: DocumentDao
) : ViewModel() {


    val documentsFlow = documentDao.getAllDocuments()

    private val _uploadStatus = MutableStateFlow(UploadStatus.IDLE)
    val uploadStatus: StateFlow<UploadStatus> = _uploadStatus.asStateFlow()

    private val _statusMessage = MutableStateFlow<String?>(null)
    val statusMessage: StateFlow<String?> = _statusMessage.asStateFlow()

    fun clearStatusMessage() {
        _statusMessage.value = null
        _uploadStatus.value = UploadStatus.IDLE
    }

    fun uploadPdf(context: Context, uri: Uri) {
        _uploadStatus.value = UploadStatus.UPLOADING
        viewModelScope.launch {
            try {
                // Copy file to local cache so we can pass an absolute path
                val cacheDir = context.cacheDir
                val fileName = getFileName(context, uri) ?: "document_${System.currentTimeMillis()}.pdf"
                val cachedFile = File(cacheDir, fileName)
                
                context.contentResolver.openInputStream(uri)?.use { inputStream ->
                    FileOutputStream(cachedFile).use { outputStream ->
                        inputStream.copyTo(outputStream)
                    }
                }

                // Upload using absolute path
                val result = repository.ingestDocument(cachedFile.absolutePath)
                result.onSuccess { response ->
                    val newDoc = DocumentEntity(
                        documentId = UUID.randomUUID().toString(),
                        name = fileName,
                        collectionId = null,
                        filePath = cachedFile.absolutePath,
                        totalPages = 0, // Mock, backend ingestion response does not provide total pages
                        totalChunks = response.total_chunks,
                        embeddingsCount = response.total_chunks,
                        indexSizeBytes = cachedFile.length(),
                        dateAdded = System.currentTimeMillis()
                    )
                    documentDao.insertDocument(newDoc)
                    _statusMessage.value = "Document uploaded successfully!"
                    _uploadStatus.value = UploadStatus.SUCCESS
                }.onFailure { error ->
                    _statusMessage.value = "Upload failed: ${error.message}"
                    _uploadStatus.value = UploadStatus.ERROR
                }
            } catch (e: Exception) {
                _statusMessage.value = "Error processing file: ${e.message}"
                _uploadStatus.value = UploadStatus.ERROR
            }
        }
    }

    fun deleteDocument(doc: DocumentEntity) {
        viewModelScope.launch {
            try {
                repository.deleteDocument(doc.name)
            } catch (e: Exception) {
                // Ignore backend delete failure if already removed
            }
            documentDao.deleteDocument(doc.documentId)
        }
    }

    fun deleteDocument(docId: String) {
        viewModelScope.launch {
            documentDao.deleteDocument(docId)
        }
    }
    
    fun reindexDocument(doc: DocumentEntity) {
        viewModelScope.launch {
            _uploadStatus.value = UploadStatus.UPLOADING
            val result = repository.ingestDocument(doc.filePath)
            result.onSuccess { response ->
                val updatedDoc = doc.copy(
                    totalChunks = response.total_chunks,
                    embeddingsCount = response.total_chunks,
                    dateAdded = System.currentTimeMillis()
                )
                documentDao.updateDocument(updatedDoc)
                _statusMessage.value = "Document re-indexed successfully!"
                _uploadStatus.value = UploadStatus.SUCCESS
            }.onFailure { error ->
                _statusMessage.value = "Re-index failed: ${error.message}"
                _uploadStatus.value = UploadStatus.ERROR
            }
        }
    }

    private fun getFileName(context: Context, uri: Uri): String? {
        var name: String? = null
        val cursor = context.contentResolver.query(uri, null, null, null, null)
        cursor?.use {
            if (it.moveToFirst()) {
                val nameIndex = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                if (nameIndex != -1) {
                    name = it.getString(nameIndex)
                }
            }
        }
        return name
    }
}
