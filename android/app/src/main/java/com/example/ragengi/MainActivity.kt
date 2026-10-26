package com.example.ragengi

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.room.Room
import com.example.ragengi.data.local.StorageManager
import com.example.ragengi.data.local.db.KnowledgeBaseDb
import com.example.ragengi.data.remote.RagApi
import com.example.ragengi.data.repository.RagRepository
import com.example.ragengi.theme.AppThemeMode
import com.example.ragengi.theme.RAGENGITheme
import com.example.ragengi.ui.screens.HomeScreen
import com.example.ragengi.ui.screens.KnowledgeBaseScreen
import com.example.ragengi.ui.screens.SettingsScreen

import com.example.ragengi.ui.screens.WelcomeScreen
import com.example.ragengi.ui.viewmodel.ChatViewModel
import com.example.ragengi.ui.viewmodel.KnowledgeBaseViewModel
import com.example.ragengi.worker.CleanupWorker
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import com.example.ragengi.R

class MainActivity : ComponentActivity() {

    companion object {
        private const val PREFS_NAME = "ragengi_prefs"
        private const val KEY_HAS_SEEN_WELCOME = "has_seen_welcome"
        private const val KEY_THEME_MODE = "theme_mode"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize UI using Compose navigation
        setContent {
            RAGENGITheme {
                MainNavigation()
            }
        }
    }
}
