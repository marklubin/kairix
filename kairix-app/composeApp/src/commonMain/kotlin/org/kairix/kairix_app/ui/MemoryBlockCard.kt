package org.kairix.kairix_app.ui

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import org.kairix.kairix_app.events.MemoryBlock

/**
 * Pastel color pairs: light background + dark accent for title/toggle
 */
private data class BlockColorScheme(
    val background: Color,
    val accent: Color
)

private val pastelSchemes = listOf(
    BlockColorScheme(Color(0xFFE8F5E9), Color(0xFF2E7D32)), // Mint / Dark Green
    BlockColorScheme(Color(0xFFE3F2FD), Color(0xFF1565C0)), // Light Blue / Dark Blue
    BlockColorScheme(Color(0xFFFCE4EC), Color(0xFFC2185B)), // Pink / Dark Pink
    BlockColorScheme(Color(0xFFFFF3E0), Color(0xFFE65100)), // Peach / Dark Orange
    BlockColorScheme(Color(0xFFF3E5F5), Color(0xFF7B1FA2)), // Lavender / Dark Purple
    BlockColorScheme(Color(0xFFE0F7FA), Color(0xFF00838F)), // Cyan / Dark Cyan
    BlockColorScheme(Color(0xFFFFFDE7), Color(0xFFF9A825)), // Cream / Dark Yellow
    BlockColorScheme(Color(0xFFEFEBE9), Color(0xFF5D4037))  // Beige / Brown
)

/**
 * Get a consistent color scheme for a block based on its label
 */
private fun getColorScheme(label: String): BlockColorScheme {
    val index = label.hashCode().let { if (it < 0) -it else it } % pastelSchemes.size
    return pastelSchemes[index]
}

/**
 * Card displaying a single memory block from the agent's context.
 */
@Composable
fun MemoryBlockCard(
    block: MemoryBlock,
    modifier: Modifier = Modifier
) {
    var expanded by remember { mutableStateOf(false) }
    val colorScheme = remember(block.label) { getColorScheme(block.label) }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = colorScheme.background
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .animateContentSize()
                .padding(16.dp)
        ) {
            // Header: label only
            Text(
                text = block.label,
                style = MaterialTheme.typography.titleSmall,
                color = colorScheme.accent
            )

            Spacer(modifier = Modifier.height(8.dp))
            HorizontalDivider(color = colorScheme.accent.copy(alpha = 0.2f))
            Spacer(modifier = Modifier.height(8.dp))

            // Block value with expand/collapse - black text
            Text(
                text = block.value,
                style = MaterialTheme.typography.bodySmall,
                color = Color.Black,
                maxLines = if (expanded) Int.MAX_VALUE else 5,
                overflow = TextOverflow.Ellipsis
            )

            // Show toggle if text is likely truncated
            if (block.value.length > 200 || block.value.count { it == '\n' } > 4) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = if (expanded) "Show less" else "Show more",
                    style = MaterialTheme.typography.labelSmall,
                    color = colorScheme.accent,
                    modifier = Modifier
                        .align(Alignment.End)
                        .clickable { expanded = !expanded }
                )
            }

            // Timestamp at bottom
            block.updatedAt?.let { timestamp ->
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = formatBlockTimestamp(timestamp),
                    style = MaterialTheme.typography.labelSmall,
                    color = colorScheme.accent.copy(alpha = 0.6f),
                    modifier = Modifier.align(Alignment.End)
                )
            }
        }
    }
}

/**
 * Format ISO timestamp for display.
 * Example: "Dec 7 14:30"
 */
private fun formatBlockTimestamp(isoTimestamp: String): String {
    return try {
        val datePart = isoTimestamp.substringBefore("T")
        val timePart = isoTimestamp.substringAfter("T").substringBefore(".")
        val timeParts = timePart.split(":")
        val time = if (timeParts.size >= 2) "${timeParts[0]}:${timeParts[1]}" else timePart

        val parts = datePart.split("-")
        if (parts.size != 3) return isoTimestamp

        val month = when (parts[1]) {
            "01" -> "Jan"; "02" -> "Feb"; "03" -> "Mar"; "04" -> "Apr"
            "05" -> "May"; "06" -> "Jun"; "07" -> "Jul"; "08" -> "Aug"
            "09" -> "Sep"; "10" -> "Oct"; "11" -> "Nov"; "12" -> "Dec"
            else -> parts[1]
        }
        val day = parts[2].trimStart('0').ifEmpty { "0" }
        "$month $day $time"
    } catch (e: Exception) {
        isoTimestamp
    }
}
