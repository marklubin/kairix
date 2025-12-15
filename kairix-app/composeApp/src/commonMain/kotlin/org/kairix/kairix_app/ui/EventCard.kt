package org.kairix.kairix_app.ui

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import org.kairix.kairix_app.events.DisplayableEvent

/**
 * Card displaying a single server event with expandable content.
 * All event-specific logic is encapsulated in DisplayableEvent implementations.
 */
@Composable
fun EventCard(
    event: DisplayableEvent,
    modifier: Modifier = Modifier
) {
    var expanded by remember { mutableStateOf(false) }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .animateContentSize()
                .padding(16.dp)
        ) {
            // Header row: event title + timestamp
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = event.title,
                    style = MaterialTheme.typography.titleSmall,
                    color = event.titleColor
                )
                Text(
                    text = formatTimestamp(event.createdAt),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(modifier = Modifier.height(8.dp))
            HorizontalDivider()
            Spacer(modifier = Modifier.height(8.dp))

            // Content lines
            event.contentLines.forEach { line ->
                Text(
                    text = line,
                    style = MaterialTheme.typography.bodyMedium
                )
            }

            // Expandable text if present
            event.expandableText?.let { text ->
                Spacer(modifier = Modifier.height(4.dp))
                ExpandableText(
                    text = text,
                    expanded = expanded,
                    onToggleExpand = { expanded = !expanded }
                )
            }
        }
    }
}

@Composable
private fun ExpandableText(
    text: String,
    expanded: Boolean,
    onToggleExpand: () -> Unit
) {
    Column {
        Text(
            text = text,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = if (expanded) Int.MAX_VALUE else 3,
            overflow = TextOverflow.Ellipsis
        )

        // Show toggle if text is likely truncated
        if (text.length > 150 || text.count { it == '\n' } > 2) {
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = if (expanded) "Show less" else "Show more",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier
                    .align(Alignment.End)
                    .clickable { onToggleExpand() }
            )
        }
    }
}

/**
 * Format ISO timestamp for display with date and time.
 * Example: "Dec 7 14:30"
 */
private fun formatTimestamp(isoTimestamp: String): String {
    return try {
        // Parse date and time parts from ISO format: "2025-12-07T14:30:00.000Z"
        val datePart = isoTimestamp.substringBefore("T")
        val timePart = isoTimestamp.substringAfter("T").substringBefore(".")
        val timeParts = timePart.split(":")
        val time = if (timeParts.size >= 2) "${timeParts[0]}:${timeParts[1]}" else timePart

        // Format: "Dec 7 14:30"
        val monthDay = formatMonthDay(datePart)
        "$monthDay $time"
    } catch (e: Exception) {
        isoTimestamp
    }
}

/**
 * Format date string to "Mon D" format.
 * Input: "2025-12-07" -> Output: "Dec 7"
 */
private fun formatMonthDay(datePart: String): String {
    val parts = datePart.split("-")
    if (parts.size != 3) return datePart

    val month = when (parts[1]) {
        "01" -> "Jan"; "02" -> "Feb"; "03" -> "Mar"; "04" -> "Apr"
        "05" -> "May"; "06" -> "Jun"; "07" -> "Jul"; "08" -> "Aug"
        "09" -> "Sep"; "10" -> "Oct"; "11" -> "Nov"; "12" -> "Dec"
        else -> parts[1]
    }
    val day = parts[2].trimStart('0').ifEmpty { "0" }
    return "$month $day"
}