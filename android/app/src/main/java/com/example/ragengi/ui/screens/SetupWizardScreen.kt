package com.example.ragengi.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.example.ragengi.data.local.StorageManager
import kotlinx.coroutines.launch

@Composable
fun SetupWizardScreen(storageManager: StorageManager, onSetupComplete: () -> Unit) {
    val coroutineScope = rememberCoroutineScope()
    var progress by remember { mutableStateOf(0) }
    var statusText by remember { mutableStateOf("Ready to configure offline models.") }
    var isInstalling by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Welcome to RAGENGI",
            style = MaterialTheme.typography.headlineMedium,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "Engineering Intelligence. Completely Offline.",
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.secondary
        )
        Spacer(modifier = Modifier.height(48.dp))

        if (isInstalling) {
            LinearProgressIndicator(
                progress = progress / 100f,
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(16.dp))
        }

        Text(
            text = statusText,
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center
        )

        if (errorMessage != null) {
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = errorMessage!!,
                color = MaterialTheme.colorScheme.error,
                textAlign = TextAlign.Center
            )
        }

        Spacer(modifier = Modifier.height(48.dp))

        Button(
            onClick = {
                isInstalling = true
                errorMessage = null
                coroutineScope.launch {
                    val result = storageManager.setupModels { p, text ->
                        progress = p
                        statusText = text
                    }
                    if (result.isSuccess) {
                        onSetupComplete()
                    } else {
                        isInstalling = false
                        errorMessage = result.exceptionOrNull()?.message ?: "Unknown error occurred"
                    }
                }
            },
            enabled = !isInstalling,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (isInstalling) "Downloading Models..." else "Start Offline Setup")
        }
    }
}
