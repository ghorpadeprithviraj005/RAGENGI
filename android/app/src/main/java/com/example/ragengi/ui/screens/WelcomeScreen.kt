package com.example.ragengi.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ragengi.R
import com.example.ragengi.theme.GothamBlack
import com.example.ragengi.theme.GothamNightNavy
import com.example.ragengi.theme.SignalYellow
import com.example.ragengi.theme.WayneTechCyan


@Composable
fun WelcomeScreen(onGetStarted: () -> Unit) {

    // --- animations ---
    val infiniteTransition = rememberInfiniteTransition(label = "welcome_anim")

    // subtle logo pulse
    val logoScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue  = 1.06f,
        animationSpec = infiniteRepeatable(
            animation  = tween(1800, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "logo_pulse"
    )

    // glow alpha for the accent ring
    val glowAlpha by infiniteTransition.animateFloat(
        initialValue = 0.35f,
        targetValue  = 0.75f,
        animationSpec = infiniteRepeatable(
            animation  = tween(1400, easing = EaseInOutSine),
            repeatMode = RepeatMode.Reverse
        ),
        label = "glow_alpha"
    )

    // button entrance fade-in (one-shot)
    val buttonAlpha by animateFloatAsState(
        targetValue  = 1f,
        animationSpec = tween(durationMillis = 1200, delayMillis = 400),
        label = "btn_alpha"
    )

    // --- layout ---
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(GothamBlack, GothamNightNavy, Color(0xFF0D1B2A))
                )
            ),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(0.dp)
        ) {

            // --- Logo ---
            Box(contentAlignment = Alignment.Center) {
                // outer glow ring
                Box(
                    modifier = Modifier
                        .size(200.dp)
                        .clip(RoundedCornerShape(48.dp))
                        .background(WayneTechCyan.copy(alpha = glowAlpha * 0.18f))
                )
                // logo image with pulse scale
                Image(
                    painter = painterResource(id = R.drawable.ragengi_logo),
                    contentDescription = "RAGENGI Logo",
                    modifier = Modifier
                        .size(180.dp)
                        .clip(RoundedCornerShape(40.dp))
                        .scale(logoScale)
                )
            }

            Spacer(modifier = Modifier.height(36.dp))

            // --- Headline ---
            Text(
                text = "Welcome to RAGENGI",
                fontSize = 28.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color.White,
                textAlign = TextAlign.Center,
                letterSpacing = 0.5.sp
            )

            Spacer(modifier = Modifier.height(10.dp))

            // Accent divider
            Box(
                modifier = Modifier
                    .width(60.dp)
                    .height(3.dp)
                    .background(
                        Brush.horizontalGradient(listOf(WayneTechCyan, SignalYellow))
                    )
            )

            Spacer(modifier = Modifier.height(14.dp))

            Text(
                text = "Your documents. Smarter answers.",
                fontSize = 16.sp,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.75f),
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 32.dp)
            )

            Spacer(modifier = Modifier.height(56.dp))

            // --- Get Started button ---
            Button(
                onClick = onGetStarted,
                modifier = Modifier
                    .fillMaxWidth(0.72f)
                    .height(54.dp),
                shape = RoundedCornerShape(27.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = SignalYellow,
                    contentColor   = GothamBlack
                ),
                elevation = ButtonDefaults.buttonElevation(defaultElevation = 6.dp)
            ) {
                Text(
                    text = "Get Started",
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 0.8.sp
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "100% Offline · Private · Secure",
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.4f),
                textAlign = TextAlign.Center
            )
        }
    }
}

// Ease alias missing in older Compose – define locally
private val EaseInOutSine = CubicBezierEasing(0.37f, 0f, 0.63f, 1f)
