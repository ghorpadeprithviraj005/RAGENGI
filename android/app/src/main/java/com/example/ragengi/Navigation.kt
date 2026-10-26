package com.example.ragengi

import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.ui.NavDisplay
import com.example.ragengi.data.local.StorageManager
import com.example.ragengi.ui.screens.WelcomeScreen

import com.example.ragengi.ui.screens.HomeScreen
import com.example.ragengi.ui.screens.KnowledgeBaseScreen
import com.example.ragengi.ui.screens.SettingsScreen
import com.example.ragengi.ui.viewmodel.ChatViewModel
import com.example.ragengi.ui.viewmodel.KnowledgeBaseViewModel

@Composable
fun MainNavigation() {
    val backStack = rememberNavBackStack(Welcome)
    val context = LocalContext.current
    NavDisplay(
        backStack = backStack,
        onBack = { backStack.removeLastOrNull() },
        entryProvider = entryProvider {
            entry<Welcome> {
                WelcomeScreen(onGetStarted = { backStack.add(Home) })
            }
// SetupWizard entry removed; navigation goes directly to Home after welcome.

            entry<Home> {
                // Provide ChatViewModel with required repository via factory
                val chatViewModel = androidx.lifecycle.viewmodel.compose.viewModel<ChatViewModel>(
                    factory = object : androidx.lifecycle.ViewModelProvider.Factory {
                        override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                            // Build Retrofit and repository
                            val okHttpClient = okhttp3.OkHttpClient.Builder()
                                .callTimeout(java.util.concurrent.TimeUnit.SECONDS.toSeconds(30), java.util.concurrent.TimeUnit.SECONDS)
                                .build()
                            val retrofit = retrofit2.Retrofit.Builder()
                                .baseUrl("http://10.0.2.2:8000/")
                                .client(okHttpClient)
                                .addConverterFactory(retrofit2.converter.gson.GsonConverterFactory.create())
                                .build()
                            val api = retrofit.create(com.example.ragengi.data.remote.RagApi::class.java)
                            val repo = com.example.ragengi.data.repository.RagRepository(api)
                            @Suppress("UNCHECKED_CAST")
                            return ChatViewModel(repo) as T
                        }
                    }
                )
                HomeScreen(
                    viewModel = chatViewModel,
                    onNavigateToKnowledgeBase = { backStack.add(KnowledgeBase) },
                    onNavigateToSettings = { backStack.add(Settings) }
                )
            }
            entry<KnowledgeBase> {
                // Provide KnowledgeBaseViewModel with repository and DAO via factory
                val kbViewModel = androidx.lifecycle.viewmodel.compose.viewModel<KnowledgeBaseViewModel>(
                    factory = object : androidx.lifecycle.ViewModelProvider.Factory {
                        override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                            // Build Retrofit and repository
                            val okHttpClient = okhttp3.OkHttpClient.Builder()
                                .callTimeout(java.util.concurrent.TimeUnit.SECONDS.toSeconds(30), java.util.concurrent.TimeUnit.SECONDS)
                                .build()
                            val retrofit = retrofit2.Retrofit.Builder()
                                .baseUrl("http://10.0.2.2:8000/")
                                .client(okHttpClient)
                                .addConverterFactory(retrofit2.converter.gson.GsonConverterFactory.create())
                                .build()
                            val api = retrofit.create(com.example.ragengi.data.remote.RagApi::class.java)
                            val repo = com.example.ragengi.data.repository.RagRepository(api)
                            // Build Room database and DAO
                            val db = androidx.room.Room.databaseBuilder(
                                context,
                                com.example.ragengi.data.local.db.KnowledgeBaseDb::class.java,
                                "knowledge_base.db"
                            ).fallbackToDestructiveMigration().build()
                            val dao = db.documentDao()
                            @Suppress("UNCHECKED_CAST")
                            return KnowledgeBaseViewModel(repo, dao) as T
                        }
                    }
                )
                KnowledgeBaseScreen(viewModel = kbViewModel, onNavigateBack = { backStack.removeLastOrNull() })
            }
            entry<Settings> {
                SettingsScreen(onNavigateBack = { backStack.removeLastOrNull() })
            }
        }
    )
}
