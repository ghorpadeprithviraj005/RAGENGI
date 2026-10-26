package com.example.ragengi.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

enum class AppThemeMode(val title: String) {
    SYSTEM("System Default"),
    DARK("Dark (Gotham Night)"),
    LIGHT("Light (Gotham Dawn)")
}

// Batman-inspired Gotham Night Color Scheme
private val GothamDarkColorScheme = darkColorScheme(
    primary = SignalYellow,
    onPrimary = GothamBlack,
    primaryContainer = GothamNightNavy,
    onPrimaryContainer = SignalYellow,
    secondary = SignalGold,
    onSecondary = GothamBlack,
    secondaryContainer = GothamSurfaceVariant,
    onSecondaryContainer = SignalYellow,
    tertiary = WayneTechCyan,
    onTertiary = GothamBlack,
    background = GothamBlack,
    onBackground = GothamLightText,
    surface = GothamCharcoal,
    onSurface = GothamLightText,
    surfaceVariant = GothamElevatedSurface,
    onSurfaceVariant = GothamMutedText,
    outline = GothamSteel,
    error = GothamCrimson,
    onError = Color.White
)

// Gotham Dawn (Clean Slate & Amber) Color Scheme
private val GothamLightColorScheme = lightColorScheme(
    primary = GothamDawnPrimary,
    onPrimary = Color.White,
    primaryContainer = GothamDawnSurfaceVariant,
    onPrimaryContainer = GothamDawnPrimary,
    secondary = GothamDawnAccent,
    onSecondary = Color.White,
    secondaryContainer = GothamDawnSurfaceVariant,
    onSecondaryContainer = GothamDawnPrimary,
    tertiary = WayneTechCyan,
    onTertiary = Color.White,
    background = GothamDawnBackground,
    onBackground = GothamDawnText,
    surface = GothamDawnSurface,
    onSurface = GothamDawnText,
    surfaceVariant = GothamDawnSurfaceVariant,
    onSurfaceVariant = GothamDawnMuted,
    outline = GothamDawnOutline,
    error = GothamCrimson,
    onError = Color.White
)

@Composable
fun RAGENGITheme(
    themeMode: AppThemeMode = AppThemeMode.DARK,
    content: @Composable () -> Unit,
) {
    val isDark = when (themeMode) {
        AppThemeMode.SYSTEM -> isSystemInDarkTheme()
        AppThemeMode.DARK -> true
        AppThemeMode.LIGHT -> false
    }

    val colorScheme = if (isDark) GothamDarkColorScheme else GothamLightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
