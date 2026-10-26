package com.example.ragengi.data.local.db

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface DocumentDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDocument(document: DocumentEntity)

    @Update
    suspend fun updateDocument(document: DocumentEntity)

    @Query("DELETE FROM documents WHERE documentId = :docId")
    suspend fun deleteDocument(docId: String)

    @Query("SELECT * FROM documents")
    fun getAllDocuments(): Flow<List<DocumentEntity>>

    @Query("SELECT * FROM documents WHERE collectionId = :collectionId")
    fun getDocumentsByCollection(collectionId: Int): Flow<List<DocumentEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertCollection(collection: DocumentCollection)

    @Query("SELECT * FROM collections")
    fun getAllCollections(): Flow<List<DocumentCollection>>
}
