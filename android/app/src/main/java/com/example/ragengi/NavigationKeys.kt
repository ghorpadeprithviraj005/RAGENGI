package com.example.ragengi

import androidx.navigation3.runtime.NavKey
import kotlinx.serialization.Serializable

@Serializable data object Main : NavKey
@Serializable data object Welcome : NavKey
@Serializable data object SetupWizard : NavKey
@Serializable data object Home : NavKey
@Serializable data object KnowledgeBase : NavKey
@Serializable data object Settings : NavKey
