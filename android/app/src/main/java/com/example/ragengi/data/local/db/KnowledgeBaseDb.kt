package com.example.ragengi.data.local.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [DocumentEntity::class, DocumentCollection::class],
    version = 1,
    exportSchema = false
)
abstract class KnowledgeBaseDb : RoomDatabase() {
    abstract fun documentDao(): DocumentDao
}
