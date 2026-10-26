package com.example.ragengi.ui.screens

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ragengi.data.model.EligibleDocument
import com.example.ragengi.data.repository.RagRepository
import com.example.ragengi.theme.AppThemeMode
import com.example.ragengi.worker.CleanupWorker
import kotlinx.coroutines.launch

// Added imports for repository creation
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import com.example.ragengi.data.remote.RagApi

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    currentTheme: AppThemeMode = AppThemeMode.SYSTEM,
    onThemeChange: (AppThemeMode) -> Unit = {},
    repository: RagRepository = run {
        val client = OkHttpClient.Builder()
            .callTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
            .build()
        val retrofit = Retrofit.Builder()
            .baseUrl("http://10.0.2.2:8000/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        RagRepository(retrofit.create(RagApi::class.java))
    },
    onNavigateBack: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val prefs = remember { context.getSharedPreferences(CleanupWorker.PREFS_NAME, Context.MODE_PRIVATE) }

    var isAutoCleanupEnabled by remember {
        mutableStateOf(prefs.getBoolean(CleanupWorker.KEY_AUTO_CLEANUP_ENABLED, false))
    }

    var eligibleDocs by remember { mutableStateOf<List<EligibleDocument>>(emptyList()) }
    var isLoadingEligible by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var actionMessage by remember { mutableStateOf<String?>(null) }

    // Dialog state for manual deletion confirmation
    var docToDelete by remember { mutableStateOf<EligibleDocument?>(null) }
    var isConfirmingCleanupAll by remember { mutableStateOf(false) }

    val fetchEligibleDocs: () -> Unit = {
        isLoadingEligible = true
        errorMessage = null
        coroutineScope.launch {
            val result = repository.getEligibleDocuments(30)
            result.onSuccess { response ->
                eligibleDocs = response.documents
                isLoadingEligible = false
            }.onFailure { err ->
                errorMessage = "Failed to load eligible documents: ${err.message}"
                isLoadingEligible = false
            }
        }
    }

    LaunchedEffect(Unit) {
        fetchEligibleDocs()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        "Settings",
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.titleLarge
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // --- THEME SELECTOR SECTION ---
            item {
                Text(
                    text = "APPEARANCE",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(8.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Theme Selection",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            text = "Choose your preferred visual atmosphere. Preferences persist across restarts.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(12.dp))

                        AppThemeMode.entries.forEach { mode ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(8.dp))
                                    .clickable { onThemeChange(mode) }
                                    .padding(vertical = 10.dp, horizontal = 8.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                RadioButton(
                                    selected = (currentTheme == mode),
                                    onClick = { onThemeChange(mode) },
                                    colors = RadioButtonDefaults.colors(
                                        selectedColor = MaterialTheme.colorScheme.primary
                                    )
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Column {
                                    Text(
                                        text = mode.title,
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = if (currentTheme == mode) FontWeight.Bold else FontWeight.Normal
                                    )
                                    val desc = when (mode) {
                                        AppThemeMode.SYSTEM -> "Follow Android system appearance"
                                        AppThemeMode.DARK -> "Original Gotham night textures and gold accents"
                                        AppThemeMode.LIGHT -> "Clean slate and daylight amber contrast"
                                    }
                                    Text(
                                        text = desc,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // --- 30-DAY INACTIVE CLEANUP SECTION ---
            item {
                Text(
                    text = "DOCUMENT STORAGE & CLEANUP",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(8.dp))

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.AutoDelete,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(28.dp)
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "30-Day Auto Cleanup",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.SemiBold
                                )
                                Text(
                                    text = if (isAutoCleanupEnabled) "Enabled (Daily WorkManager scheduled)" else "Disabled (Default OFF)",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = if (isAutoCleanupEnabled) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            Switch(
                                checked = isAutoCleanupEnabled,
                                onCheckedChange = { enabled ->
                                    isAutoCleanupEnabled = enabled
                                    prefs.edit().putBoolean(CleanupWorker.KEY_AUTO_CLEANUP_ENABLED, enabled).apply()
                                    if (enabled) {
                                        CleanupWorker.scheduleDaily(context)
                                        actionMessage = "Auto cleanup enabled. Daily background job scheduled."
                                    } else {
                                        CleanupWorker.cancel(context)
                                        actionMessage = "Auto cleanup disabled. Background job cancelled."
                                    }
                                    fetchEligibleDocs()
                                },
                                colors = SwitchDefaults.colors(
                                    checkedThumbColor = MaterialTheme.colorScheme.onPrimary,
                                    checkedTrackColor = MaterialTheme.colorScheme.primary
                                )
                            )
                        }

                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = "Policy: Documents inactive for 30 consecutive days will be safely deleted, including original files, extracted text, embeddings, and FAISS vectors. Model files, system components, and actively opened documents are strictly protected and never deleted.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // --- ELIGIBLE DOCUMENTS LIST HEADER ---
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "ELIGIBLE FOR CLEANUP (${eligibleDocs.size})",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold
                    )
                    IconButton(onClick = fetchEligibleDocs) {
                        Icon(
                            Icons.Default.Refresh,
                            contentDescription = "Refresh",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }

            if (isLoadingEligible) {
                item {
                    Box(modifier = Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                    }
                }
            } else if (eligibleDocs.isEmpty()) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f))
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.CheckCircle,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Text(
                                text = "All documents are up-to-date. No inactive documents exceed the 30-day threshold.",
                                style = MaterialTheme.typography.bodyMedium
                            )
                        }
                    }
                }
            } else {
                items(eligibleDocs) { doc ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.Description,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(32.dp)
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = doc.filename,
                                    style = MaterialTheme.typography.bodyMedium,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = "Inactive for ${doc.inactive_days} days (${doc.vector_count} vectors, ${formatBytes(doc.file_size_bytes)})",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            IconButton(onClick = { docToDelete = doc }) {
                                Icon(
                                    Icons.Default.DeleteOutline,
                                    contentDescription = "Delete",
                                    tint = MaterialTheme.colorScheme.error
                                )
                            }
                        }
                    }
                }

                item {
                    Button(
                        onClick = { isConfirmingCleanupAll = true },
                        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                    ) {
                        Icon(Icons.Default.DeleteSweep, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Clean Up All Eligible Documents Now")
                    }
                }
            }

            // Notification banners
            if (actionMessage != null) {
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
                    ) {
                        Text(
                            text = actionMessage ?: "",
                            modifier = Modifier.padding(12.dp),
                            color = MaterialTheme.colorScheme.onPrimaryContainer,
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }
            }
            if (errorMessage != null) {
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
                    ) {
                        Text(
                            text = errorMessage ?: "",
                            modifier = Modifier.padding(12.dp),
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }
            }
        }
    }

    // --- CONFIRMATION DIALOG: SINGLE DOCUMENT ---
    docToDelete?.let { doc ->
        AlertDialog(
            onDismissRequest = { docToDelete = null },
            icon = { Icon(Icons.Default.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.error) },
            title = { Text("Permanently Delete Document?") },
            text = {
                Text(
                    "Are you sure you want to delete '${doc.filename}'? This will permanently remove the original file, extracted text, embeddings, and FAISS index entries. This action cannot be undone."
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        val target = doc.filename
                        docToDelete = null
                        coroutineScope.launch {
                            val res = repository.deleteDocument(target)
                            res.onSuccess {
                                actionMessage = "Successfully removed '${target}' and its vectors."
                                fetchEligibleDocs()
                            }.onFailure { err ->
                                errorMessage = "Deletion failed: ${err.message}"
                            }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text("Delete Permanently")
                }
            },
            dismissButton = {
                TextButton(onClick = { docToDelete = null }) {
                    Text("Cancel")
                }
            }
        )
    }

    // --- CONFIRMATION DIALOG: CLEAN UP ALL ELIGIBLE ---
    if (isConfirmingCleanupAll) {
        AlertDialog(
            onDismissRequest = { isConfirmingCleanupAll = false },
            icon = { Icon(Icons.Default.DeleteSweep, contentDescription = null, tint = MaterialTheme.colorScheme.error) },
            title = { Text("Clean Up All Inactive Documents?") },
            text = {
                Text(
                    "This will delete ${eligibleDocs.size} documents inactive for more than 30 days along with their embeddings and FAISS index entries. Active documents and models will NOT be touched. Continue?"
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        isConfirmingCleanupAll = false
                        coroutineScope.launch {
                            val res = repository.runCleanup(30)
                            res.onSuccess { response ->
                                actionMessage = "Cleanup completed: removed ${response.deleted_documents.size} documents, ${response.total_vectors_removed} vectors, freed ${formatBytes(response.freed_bytes)}."
                                fetchEligibleDocs()
                            }.onFailure { err ->
                                errorMessage = "Cleanup failed: ${err.message}"
                            }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text("Clean Up All")
                }
            },
            dismissButton = {
                TextButton(onClick = { isConfirmingCleanupAll = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}

private fun formatBytes(bytes: Long): String {
    if (bytes <= 0) return "0 B"
    val kb = bytes / 1024.0
    if (kb < 1024) return "${"%.1f".format(kb)} KB"
    val mb = kb / 1024.0
    return "${"%.2f".format(mb)} MB"
}
