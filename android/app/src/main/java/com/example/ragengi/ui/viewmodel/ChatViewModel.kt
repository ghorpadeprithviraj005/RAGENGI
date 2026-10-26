package com.example.ragengi.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import android.util.Log
import com.example.ragengi.data.model.ChatMessage
import com.example.ragengi.data.repository.RagRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ChatViewModel(private val repository: RagRepository) : ViewModel() {

    // Secondary constructor for Compose default creation without manual factory
    constructor() : this(
        RagRepository(
            retrofit2.Retrofit.Builder()
                .baseUrl("http://10.0.2.2:8000/")
                .client(
                    okhttp3.OkHttpClient.Builder()
                        .callTimeout(java.util.concurrent.TimeUnit.SECONDS.toMillis(210), java.util.concurrent.TimeUnit.MILLISECONDS)
                        .readTimeout(java.util.concurrent.TimeUnit.SECONDS.toMillis(210), java.util.concurrent.TimeUnit.MILLISECONDS)
                        .writeTimeout(java.util.concurrent.TimeUnit.SECONDS.toMillis(210), java.util.concurrent.TimeUnit.MILLISECONDS)
                        .build()
                )
                .addConverterFactory(retrofit2.converter.gson.GsonConverterFactory.create())
                .build()
                .create(com.example.ragengi.data.remote.RagApi::class.java)
        )
    )

    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages.asStateFlow()

    // Keep the last assistant answer to provide continuity.
    private var lastAssistantMessage: String? = null

    // Optional active document filename for scoped retrieval.
    private var activeDocument: String? = null

    /** Set the active document filename that the backend should prioritize */
    fun setActiveDocument(filename: String?) {
        activeDocument = filename
        Log.d("ChatViewModel", "Active document set to: $activeDocument")
    }

    fun sendMessage(query: String) {
        val userMsg = ChatMessage(text = query, isUser = true)
        val typingMsg = ChatMessage(text = "Analyzing...", isUser = false, isTyping = true)

        // Append user message and typing indicator.
        _messages.value = _messages.value + listOf(userMsg, typingMsg)

        viewModelScope.launch {
            val startTime = System.currentTimeMillis()
            Log.d("ChatViewModel", "Sending query: '$query' with activeDocument=$activeDocument")
            val result = repository.askQuestion(query, activeDocument)
            val duration = System.currentTimeMillis() - startTime
            Log.d("ChatViewModel", "Received response in ${duration}ms")

            // Remove typing indicator.
            val currentList = _messages.value.filter { !it.isTyping }.toMutableList()

            result.onSuccess { response ->
                currentList.add(
                    ChatMessage(
                        text = response.answer,
                        isUser = false,
                        citations = response.citations
                    )
                )
                // Store answer for next turn.
                lastAssistantMessage = response.answer
            }.onFailure { error ->
                currentList.add(
                    ChatMessage(
                        text = "Error: ${error.message ?: "Could not connect to offline model."}",
                        isUser = false
                    )
                )
                // Reset stored answer on error.
                lastAssistantMessage = null
            }

            _messages.value = currentList
        }
    }
}

