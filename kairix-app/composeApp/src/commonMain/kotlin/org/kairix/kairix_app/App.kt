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
import org.kairix.kairix_app.voice.Voice
import org.kairix.kairix_app.voice.VoiceApiClient
import org.kairix.kairix_app.voice.VoiceSession

enum class Endpoint(
    val label: String,
    val baseUrl: String,
    val voiceUrl: String,
    val eventsUrl: String,
    val agentId: String
) {
    CARRIZO(
        label = "Carrizo",
        baseUrl = "http://100.86.139.116:8000",
        voiceUrl = "ws://100.86.139.116:8000/voice",
        eventsUrl = "ws://100.86.139.116:8000/events/agent-62f4b273-69c4-41d3-8571-02a0413756fb",
        agentId = "agent-62f4b273-69c4-41d3-8571-02a0413756fb"
    ),
    SALINAS(
        label = "Salinas",
        baseUrl = "http://100.120.96.128:8000",
        voiceUrl = "ws://100.120.96.128:8000/voice",
        eventsUrl = "ws://100.120.96.128:8000/events/agent-56a10649-420a-4639-83f3-575e12964442",
        agentId = "agent-56a10649-420a-4639-83f3-575e12964442"
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

        // Voice state
        var voices by remember { mutableStateOf(emptyList<Voice>()) }
        var currentVoice by remember { mutableStateOf<Voice?>(null) }
        var selectedVoice by remember { mutableStateOf<Voice?>(null) }
        var isLoadingVoices by remember { mutableStateOf(false) }
        var isSavingVoice by remember { mutableStateOf(false) }
        var voiceSaveError by remember { mutableStateOf<String?>(null) }

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

        // Load voices and current agent voice when settings tab is selected or endpoint changes
        LaunchedEffect(currentScreen, selectedEndpoint) {
            if (currentScreen != AppScreen.Settings) return@LaunchedEffect

            isLoadingVoices = true
            voiceSaveError = null
            selectedVoice = null
            val apiClient = VoiceApiClient(selectedEndpoint.baseUrl)
            try {
                voices = apiClient.listVoices()
                val agentSettings = apiClient.getAgentVoice(selectedEndpoint.agentId)
                currentVoice = agentSettings.voice
            } catch (e: Exception) {
                println("Failed to load voices: ${e.message}")
                voiceSaveError = "Failed to load voices: ${e.message}"
            } finally {
                isLoadingVoices = false
            }
        }

        // Save voice callback
        val onSaveVoice: () -> Unit = {
            selectedVoice?.let { voice ->
                scope.launch {
                    isSavingVoice = true
                    voiceSaveError = null
                    val apiClient = VoiceApiClient(selectedEndpoint.baseUrl)
                    try {
                        apiClient.setAgentVoice(selectedEndpoint.agentId, voice.id)
                        currentVoice = voice
                        selectedVoice = null
                    } catch (e: Exception) {
                        voiceSaveError = "Failed to save voice"
                    } finally {
                        isSavingVoice = false
                    }
                }
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
                                    ConnectionState.DISCONNECTED -> voiceSession.connect(selectedEndpoint.voiceUrl, selectedEndpoint.agentId)
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
                            connectionState = connectionState,
                            voices = voices,
                            currentVoice = currentVoice,
                            selectedVoice = selectedVoice,
                            onVoiceSelected = { selectedVoice = it },
                            onSaveVoice = onSaveVoice,
                            isLoadingVoices = isLoadingVoices,
                            isSavingVoice = isSavingVoice,
                            voiceSaveError = voiceSaveError
                        )
                    }
                }
            }
        }
    }
}
