package org.kairix.kairix_app

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MicOff
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.kairix.kairix_app.db.DriverFactory
import org.kairix.kairix_app.db.EventRepository
import org.kairix.kairix_app.events.EventSession
import org.kairix.kairix_app.theme.KairixTheme
import org.kairix.kairix_app.ui.EventCard
import org.kairix.kairix_app.voice.VoiceSession

enum class Endpoint(val label: String, val voiceUrl: String, val eventsUrl: String) {
    CARRIZO(
        "Carrizo",
        "ws://100.86.139.116:8000/voice",
        "ws://100.86.139.116:8000/events/agent-62f4b273-69c4-41d3-8571-02a0413756fb"
    ),
    SALINAS(
        "Salinas",
        "ws://100.120.96.128:8000/voice",
        "ws://100.120.96.128:8000/events/agent-56a10649-420a-4639-83f3-575e12964442"
    ),
}

@Composable
fun App() {
    KairixTheme {
        val scope = rememberCoroutineScope()
        val voiceSession = remember { VoiceSession() }

        // Initialize database and repository
        val repository = remember { EventRepository(DriverFactory()) }
        val eventSession = remember { EventSession(repository) }

        val connectionState by voiceSession.state.collectAsState()
        var selectedEndpoint by remember { mutableStateOf(Endpoint.CARRIZO) }

        // Events state
        val events by eventSession.events.collectAsState()
        val listState = rememberLazyListState()

        // Load persisted events then connect to WebSocket
        // Both in same block to ensure proper sequencing
        LaunchedEffect(selectedEndpoint) {
            eventSession.disconnect()
            eventSession.loadPersistedEvents()  // Load from DB first
            try {
                eventSession.connect(selectedEndpoint.eventsUrl)
            } catch (e: Exception) {
                println("Failed to connect to events: ${e.message}")
            }
        }

        // Cleanup on dispose
        DisposableEffect(Unit) {
            onDispose {
                eventSession.disconnect()
            }
        }

        // Auto-scroll to bottom when new events arrive
        LaunchedEffect(events.size) {
            if (events.isNotEmpty()) {
                listState.animateScrollToItem(events.size - 1)
            }
        }

        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp)
                    .padding(top = 48.dp)  // Clear camera cutout
                    .padding(bottom = 100.dp), // Space for FAB
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Status
                Text(
                    text = when (connectionState) {
                        ConnectionState.DISCONNECTED -> "Ready"
                        ConnectionState.CONNECTED -> "Listening..."
                        ConnectionState.CONNECTING -> "Connecting..."
                        ConnectionState.ERROR -> "Error"
                    },
                    style = MaterialTheme.typography.headlineMedium,
                    color = MaterialTheme.colorScheme.onBackground
                )

                // Endpoint selector
                Row(
                    modifier = Modifier.padding(top = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Endpoint.entries.forEach { endpoint ->
                        FilterChip(
                            selected = selectedEndpoint == endpoint,
                            onClick = {
                                if (connectionState == ConnectionState.DISCONNECTED) {
                                    selectedEndpoint = endpoint
                                }
                            },
                            label = { Text(endpoint.label) },
                            enabled = connectionState == ConnectionState.DISCONNECTED
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Events list
                if (events.isEmpty()) {
                    Text(
                        text = "Waiting for events...",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxWidth(),
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

            // Mic button at bottom center
            FloatingActionButton(
                onClick = {
                    scope.launch {
                        when (connectionState) {
                            ConnectionState.DISCONNECTED -> voiceSession.connect(selectedEndpoint.voiceUrl)
                            ConnectionState.CONNECTED -> voiceSession.disconnect()
                            else -> { /* ignore during connecting/error */ }
                        }
                    }
                },
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 32.dp)
                    .size(80.dp),
                containerColor = when (connectionState) {
                    ConnectionState.CONNECTED -> MaterialTheme.colorScheme.primary
                    else -> MaterialTheme.colorScheme.surfaceVariant
                }
            ) {
                Icon(
                    imageVector = when (connectionState) {
                        ConnectionState.CONNECTED -> Icons.Filled.Mic
                        else -> Icons.Filled.MicOff
                    },
                    contentDescription = if (connectionState == ConnectionState.CONNECTED) "Stop" else "Start",
                    modifier = Modifier.size(36.dp)
                )
            }
        }
    }
}