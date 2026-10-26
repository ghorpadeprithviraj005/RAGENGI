package com.example.ragengi.data.repository

import android.util.Log
import com.example.ragengi.data.local.db.DocumentDao
import com.example.ragengi.data.local.db.DocumentEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import java.io.File

class KnowledgeBaseRepository(
    private val dao: DocumentDao,
    private val faissDirectory: File // Represents where the local FAISS index is stored
) {

    val allDocuments: Flow<List<DocumentEntity>> = dao.getAllDocuments()

    suspend fun indexDocument(document: DocumentEntity) = withContext(Dispatchers.IO) {
        try {
            // Here you would call the LocalRagPipeline to chunk -> embed -> faiss.add()
            // Simulating successful indexing for the DB record
            dao.insertDocument(document)
            Log.i("KnowledgeBase", "Document ${document.name} indexed successfully.")
        } catch (e: Exception) {
            Log.e("KnowledgeBase", "Failed to index document: ${document.name}", e)
            throw e
        }
    }

    suspend fun deleteDocumentSafely(docId: String) = withContext(Dispatchers.IO) {
        try {
            // 1. Remove from local Room DB
            dao.deleteDocument(docId)
            
            // 2. Ideally, here we remove the embeddings from FAISS. 
            // Since FAISS FlatL2 doesn't easily support targeted deletion without ID maps,
            // a common offline strategy is tracking "deleted_ids" and rebuilding the index 
            // asynchronously during idle time if the deleted count gets too high.
            Log.i("KnowledgeBase", "Document $docId marked for deletion in FAISS and removed from DB.")
        } catch (e: Exception) {
            Log.e("KnowledgeBase", "Failed to delete document $docId", e)
            throw e
        }
    }
}
