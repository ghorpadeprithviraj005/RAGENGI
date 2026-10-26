package com.example.ragengi.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.example.ragengi.data.model.EngineeringAnswer

/**
 * Renders a structured engineering answer in the chat UI.
 * Shows domain badge, formulas, standards, units, figures, and citations
 * in collapsible sections for a clean experience.
 */
@Composable
fun EngineeringAnswerCard(answer: EngineeringAnswer) {
    Column(
        modifier = Modifier
            .fillMaxWidth(0.92f)
            .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(12.dp))
            .padding(14.dp)
    ) {
        // Domain Badge
        DomainBadge(domain = answer.domain)

        Spacer(modifier = Modifier.height(10.dp))

        // Technical Summary
        Text(
            text = answer.technicalSummary,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface
        )

        // Formula Section
        if (answer.formulas.isNotEmpty()) {
            Spacer(modifier = Modifier.height(10.dp))
            ExpandableSection(title = "Formulas (${answer.formulas.size})") {
                answer.formulas.forEach { formula ->
                    Text(
                        text = "  • $formula",
                        style = MaterialTheme.typography.bodySmall.copy(
                            fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace
                        ),
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }

        // Standards Section
        if (answer.standards.isNotEmpty()) {
            Spacer(modifier = Modifier.height(8.dp))
            ExpandableSection(title = "Standards Referenced (${answer.standards.size})") {
                answer.standards.forEach { std ->
                    Text(
                        text = "  • $std",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.tertiary
                    )
                }
            }
        }

        // Units Section
        if (answer.units.isNotEmpty()) {
            Spacer(modifier = Modifier.height(8.dp))
            ExpandableSection(title = "Engineering Units Detected") {
                answer.units.forEach { unit ->
                    Text(
                        text = "  • $unit",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        // Figure References
        if (answer.figureReferences.isNotEmpty()) {
            Spacer(modifier = Modifier.height(8.dp))
            ExpandableSection(title = "Figures / Tables") {
                answer.figureReferences.forEach { ref ->
                    Text(
                        text = "  • $ref",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.secondary
                    )
                }
            }
        }

        // Citations
        if (answer.citations.isNotEmpty()) {
            Spacer(modifier = Modifier.height(8.dp))
            Divider(thickness = 0.5.dp, color = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Citations: " + answer.citations.joinToString(" • ") {
                    "[P${it.page_number}, C${it.chunk_id}]"
                },
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.secondary
            )
        }
    }
}

@Composable
fun DomainBadge(domain: String) {
    val color = when {
        domain.contains("Civil", ignoreCase = true)       -> Color(0xFF4CAF50)
        domain.contains("Mechanical", ignoreCase = true)  -> Color(0xFFFF9800)
        domain.contains("Electrical", ignoreCase = true)  -> Color(0xFF2196F3)
        domain.contains("Computer", ignoreCase = true)    -> Color(0xFF9C27B0)
        else                                               -> Color(0xFF607D8B)
    }

    Surface(
        color = color.copy(alpha = 0.15f),
        shape = RoundedCornerShape(50),
        tonalElevation = 0.dp
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .background(color, RoundedCornerShape(50))
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = domain,
                style = MaterialTheme.typography.labelSmall,
                color = color
            )
        }
    }
}

@Composable
fun ExpandableSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    var expanded by remember { mutableStateOf(false) }

    TextButton(onClick = { expanded = !expanded }, contentPadding = PaddingValues(0.dp)) {
        Text(
            text = (if (expanded) "▼ " else "▶ ") + title,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }

    if (expanded) {
        Column(modifier = Modifier.padding(start = 8.dp)) {
            content()
        }
    }
}
