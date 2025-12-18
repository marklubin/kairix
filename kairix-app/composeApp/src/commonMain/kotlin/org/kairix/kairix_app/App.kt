package org.kairix.kairix_app

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.FiberManualRecord
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.kairix.kairix_app.db.DriverFactory
import org.kairix.kairix_app.db.EventRepository
import org.kairix.kairix_app.events.ContextStateEvent
import org.kairix.kairix_app.events.EventSession
import org.kairix.kairix_app.events.MemoryBlock
import org.kairix.kairix_app.navigation.AppBottomNavBar
import org.kairix.kairix_app.navigation.AppScreen
import org.kairix.kairix_app.theme.KairixTheme
import org.kairix.kairix_app.ui.ContextView
import org.kairix.kairix_app.ui.EventsView
import org.kairix.kairix_app.ui.SettingsView
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
        var selectedEndpoint by remember { mutableStateOf(Endpoint.SALINAS) }
        var currentScreen by remember { mutableStateOf(AppScreen.Events) }

        // Events state
        val events by eventSession.events.collectAsState()
        val listState = rememberLazyListState()

        // Memory blocks state - extract from latest ContextStateEvent
        var currentBlocks by remember { mutableStateOf(emptyList<MemoryBlock>()) }

        // Update blocks when events change
        LaunchedEffect(events) {
            // Find the most recent ContextStateEvent
            val latestContextEvent = events.filterIsInstance<ContextStateEvent>().lastOrNull()
            latestContextEvent?.let { currentBlocks = it.blocks }
        }

        // Load persisted events then connect to WebSocket
        LaunchedEffect(selectedEndpoint) {
            eventSession.disconnect()
            eventSession.loadPersistedEvents()
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

        // Auto-scroll events to bottom when new events arrive
        LaunchedEffect(events.size) {
            if (events.isNotEmpty() && currentScreen == AppScreen.Events) {
                listState.animateScrollToItem(events.size - 1)
            }
        }

        Scaffold(
            bottomBar = {
                AppBottomNavBar(
                    currentScreen = currentScreen,
                    onScreenSelected = { currentScreen = it }
                )
            }
        ) { paddingValues ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .padding(horizontal = 16.dp)
                    .padding(top = 48.dp), // Clear camera cutout
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Status header with record button
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Status text
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

                    // Record/Pause button
                    IconButton(
                        onClick = {
                            scope.launch {
                                when (connectionState) {
                                    ConnectionState.DISCONNECTED -> voiceSession.connect(selectedEndpoint.voiceUrl)
                                    ConnectionState.CONNECTED -> voiceSession.disconnect()
                                    else -> { /* ignore during connecting/error */ }
                                }
                            }
                        },
                        enabled = connectionState != ConnectionState.CONNECTING
                    ) {
                        Icon(
                            imageVector = when (connectionState) {
                                ConnectionState.CONNECTED -> Icons.Filled.Pause
                                else -> Icons.Filled.FiberManualRecord
                            },
                            contentDescription = if (connectionState == ConnectionState.CONNECTED) "Pause" else "Record",
                            tint = when (connectionState) {
                                ConnectionState.CONNECTED -> MaterialTheme.colorScheme.primary
                                ConnectionState.ERROR -> MaterialTheme.colorScheme.error
                                else -> MaterialTheme.colorScheme.error.copy(alpha = 0.7f)
                            },
                            modifier = Modifier.size(32.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Content based on current screen
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f)
                ) {
                    when (currentScreen) {
                        AppScreen.Events -> EventsView(
                            events = events,
                            listState = listState
                        )
                        AppScreen.Context -> ContextView(
                            blocks = currentBlocks
                        )
                        AppScreen.Settings -> SettingsView(
                            selectedEndpoint = selectedEndpoint,
                            onEndpointSelected = { selectedEndpoint = it },
                            connectionState = connectionState
                        )
                    }
                }
            }
        }
    }
}
