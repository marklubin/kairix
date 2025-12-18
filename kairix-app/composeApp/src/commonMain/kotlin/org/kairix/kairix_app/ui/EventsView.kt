package org.kairix.kairix_app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import org.kairix.kairix_app.events.DisplayableEvent

/**
 * View displaying the event stream from the agent.
 */
@Composable
fun EventsView(
    events: List<DisplayableEvent>,
    listState: LazyListState,
    modifier: Modifier = Modifier
) {
    if (events.isEmpty()) {
        Box(
            modifier = modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "Waiting for events...",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    } else {
        LazyColumn(
            state = listState,
            modifier = modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(
                items = events,
                key = { it.id }
            ) { event ->
                EventCard(event = event)
            }
        }
    }
}
