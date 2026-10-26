package com.example.ragengi.data.local.db

import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.ColumnInfo

@Entity(tableName = "collections")
data class DocumentCollection(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val name: String,
    val description: String? = null
)

@Entity(tableName = "documents")
data class DocumentEntity(
    @PrimaryKey val documentId: String, // E.g., UUID or filename hash
    val name: String,
    val collectionId: Int?,
    val filePath: String,
    
    // Statistics
    val totalPages: Int,
    val totalChunks: Int,
    val embeddingsCount: Int,
    val indexSizeBytes: Long,
    
    val dateAdded: Long = System.currentTimeMillis()
)
