package org.kairix.kairix_app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import org.kairix.kairix_app.events.MemoryBlock

/**
 * View displaying the current memory blocks from the agent's context.
 */
@Composable
fun ContextView(
    blocks: List<MemoryBlock>,
    modifier: Modifier = Modifier
) {
    if (blocks.isEmpty()) {
        Box(
            modifier = modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "No context data yet...",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    } else {
        LazyColumn(
            modifier = modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(
                count = blocks.size,
                key = { index -> "${index}_${blocks[index].label}" }
            ) { index ->
                MemoryBlockCard(block = blocks[index])
            }
        }
    }
}
