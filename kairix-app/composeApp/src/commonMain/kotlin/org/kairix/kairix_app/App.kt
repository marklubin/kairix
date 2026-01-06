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
import org.kairix.kairix_app.chat.ChatSession
import org.kairix.kairix_app.db.*
import org.kairix.kairix_app.endpoints.EndpointConfig
import org.kairix.kairix_app.events.ContextStateEvent
import org.kairix.kairix_app.events.EventSession
import org.kairix.kairix_app.events.MemoryBlock
import org.kairix.kairix_app.navigation.AppBottomNavBar
import org.kairix.kairix_app.navigation.AppScreen
import org.kairix.kairix_app.theme.KairixTheme
import org.kairix.kairix_app.ui.*
import org.kairix.kairix_app.voice.Voice
import org.kairix.kairix_app.voice.VoiceApiClient
import org.kairix.kairix_app.voice.VoiceSession

@Composable
fun App() {
    KairixTheme {
        val scope = rememberCoroutineScope()

        // Initialize database
        val database = remember { KairixDatabase(DriverFactory().createDriver()) }

        // Initialize repositories
        val eventRepository = remember { EventRepository(DriverFactory()) }
        val endpointRepository = remember { EndpointRepository(database) }
        val chatRepository = remember { ChatRepository(database) }

        // Initialize sessions
        val voiceSession = remember { VoiceSession() }
        val eventSession = remember { EventSession(eventRepository) }
        val chatSession = remember { ChatSession(chatRepository) }

        // Connection state
        val connectionState by voiceSession.state.collectAsState()

        // Endpoint state
        var endpoints by remember { mutableStateOf(emptyList<EndpointConfig>()) }
        var selectedEndpoint by remember { mutableStateOf<EndpointConfig?>(null) }
        var isLoadingEndpoints by remember { mutableStateOf(true) }

        // Navigation state
        var currentScreen by remember { mutableStateOf(AppScreen.Events) }

        // Events state
        val events by eventSession.events.collectAsState()
        val listState = rememberLazyListState()

        // Memory blocks state - extract from latest ContextStateEvent
        var currentBlocks by remember { mutableStateOf(emptyList<MemoryBlock>()) }

        // Chat state
        val chatMessages by chatSession.messages.collectAsState()
        val isChatConnected by chatSession.isConnected.collectAsState()

        // Voice state
        var voices by remember { mutableStateOf(emptyList<Voice>()) }
        var currentVoice by remember { mutableStateOf<Voice?>(null) }
        var selectedVoice by remember { mutableStateOf<Voice?>(null) }
        var isLoadingVoices by remember { mutableStateOf(false) }
        var isSavingVoice by remember { mutableStateOf(false) }
        var voiceSaveError by remember { mutableStateOf<String?>(null) }

        // Load endpoints on startup and seed defaults
        LaunchedEffect(Unit) {
            endpointRepository.seedDefaultsIfEmpty()
            endpoints = endpointRepository.getAllEndpoints()
            selectedEndpoint = endpointRepository.getSelectedEndpoint() ?: endpoints.firstOrNull()
            isLoadingEndpoints = false
        }

        // Update blocks when events change
        LaunchedEffect(events) {
            val latestContextEvent = events.filterIsInstance<ContextStateEvent>().lastOrNull()
            latestContextEvent?.let { currentBlocks = it.blocks }
        }

        // Connect to events WebSocket when endpoint changes
        LaunchedEffect(selectedEndpoint) {
            val endpoint = selectedEndpoint ?: return@LaunchedEffect
            eventSession.disconnect()
            eventSession.loadPersistedEvents()
            try {
                eventSession.connect(endpoint.eventsUrl)
            } catch (e: Exception) {
                println("Failed to connect to events: ${e.message}")
            }
        }

        // Connect to chat WebSocket when endpoint changes
        LaunchedEffect(selectedEndpoint) {
            val endpoint = selectedEndpoint ?: return@LaunchedEffect
            chatSession.disconnect()
            chatSession.loadHistory(endpoint.agentId)
            try {
                chatSession.connect(endpoint.chatUrl, endpoint.agentId)
            } catch (e: Exception) {
                println("Failed to connect to chat: ${e.message}")
            }
        }

        // Load voices when settings tab is selected
        LaunchedEffect(currentScreen, selectedEndpoint) {
            if (currentScreen != AppScreen.Settings) return@LaunchedEffect
            val endpoint = selectedEndpoint ?: return@LaunchedEffect

            isLoadingVoices = true
            voiceSaveError = null
            selectedVoice = null
            val apiClient = VoiceApiClient(endpoint.baseUrl)
            try {
                voices = apiClient.listVoices()
                val agentSettings = apiClient.getAgentVoice(endpoint.agentId)
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
                val endpoint = selectedEndpoint
                if (endpoint != null) {
                    scope.launch {
                        isSavingVoice = true
                        voiceSaveError = null
                        val apiClient = VoiceApiClient(endpoint.baseUrl)
                        try {
                            apiClient.setAgentVoice(endpoint.agentId, voice.id)
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
        }

        // Endpoint selection callback
        val onEndpointSelected: (EndpointConfig) -> Unit = { endpoint ->
            if (connectionState == ConnectionState.DISCONNECTED) {
                scope.launch {
                    endpointRepository.setSelectedEndpoint(endpoint.id)
                    selectedEndpoint = endpoint
                }
            }
        }

        // Send chat message callback
        val onSendChatMessage: (String) -> Unit = { text ->
            scope.launch {
                chatSession.sendMessage(text)
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
                    .padding(top = 48.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Status header with record button (only show for non-chat screens)
                if (currentScreen != AppScreen.Chat) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
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

                        IconButton(
                            onClick = {
                                val endpoint = selectedEndpoint
                                if (endpoint != null) {
                                    scope.launch {
                                        when (connectionState) {
                                            ConnectionState.DISCONNECTED -> voiceSession.connect(
                                                endpoint.voiceUrl,
                                                endpoint.agentId
                                            )
                                            ConnectionState.CONNECTED -> voiceSession.disconnect()
                                            else -> { /* ignore */ }
                                        }
                                    }
                                }
                            },
                            enabled = connectionState != ConnectionState.CONNECTING && selectedEndpoint != null
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
                }

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
                        AppScreen.Chat -> ChatView(
                            messages = chatMessages,
                            onSendMessage = onSendChatMessage,
                            isConnected = isChatConnected
                        )
                        AppScreen.Context -> ContextView(
                            blocks = currentBlocks
                        )
                        AppScreen.Settings -> SettingsView(
                            endpoints = endpoints,
                            selectedEndpoint = selectedEndpoint,
                            onEndpointSelected = onEndpointSelected,
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
