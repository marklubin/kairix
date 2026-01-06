package org.kairix.kairix_app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import org.kairix.kairix_app.ConnectionState
import org.kairix.kairix_app.endpoints.EndpointConfig
import org.kairix.kairix_app.voice.Voice

/**
 * Settings view for configuring the app.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsView(
    endpoints: List<EndpointConfig>,
    selectedEndpoint: EndpointConfig?,
    onEndpointSelected: (EndpointConfig) -> Unit,
    connectionState: ConnectionState,
    voices: List<Voice>,
    currentVoice: Voice?,
    selectedVoice: Voice?,
    onVoiceSelected: (Voice) -> Unit,
    onSaveVoice: () -> Unit,
    isLoadingVoices: Boolean,
    isSavingVoice: Boolean,
    voiceSaveError: String?,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        // Endpoint selection
        Text(
            text = "Endpoint",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onBackground
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "Select which server to connect to",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Endpoint dropdown
        var endpointExpanded by remember { mutableStateOf(false) }

        ExposedDropdownMenuBox(
            expanded = endpointExpanded,
            onExpandedChange = {
                if (connectionState == ConnectionState.DISCONNECTED) {
                    endpointExpanded = it
                }
            }
        ) {
            OutlinedTextField(
                value = selectedEndpoint?.label ?: "Select endpoint",
                onValueChange = {},
                readOnly = true,
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = endpointExpanded) },
                modifier = Modifier
                    .fillMaxWidth()
                    .menuAnchor(ExposedDropdownMenuAnchorType.PrimaryNotEditable, enabled = true),
                enabled = connectionState == ConnectionState.DISCONNECTED
            )
            ExposedDropdownMenu(
                expanded = endpointExpanded,
                onDismissRequest = { endpointExpanded = false }
            ) {
                endpoints.forEach { endpoint ->
                    DropdownMenuItem(
                        text = {
                            Column {
                                Text(endpoint.label)
                                Text(
                                    text = endpoint.agentId,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        },
                        onClick = {
                            onEndpointSelected(endpoint)
                            endpointExpanded = false
                        }
                    )
                }
            }
        }

        if (connectionState != ConnectionState.DISCONNECTED) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Disconnect to change endpoint",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error
            )
        }

        Spacer(modifier = Modifier.height(32.dp))
        HorizontalDivider()
        Spacer(modifier = Modifier.height(16.dp))

        // Voice selection
        Text(
            text = "Voice",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onBackground
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "Select the voice for this agent",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(16.dp))

        if (isLoadingVoices) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp))
                Text(
                    text = "Loading voices...",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        } else {
            var voiceExpanded by remember { mutableStateOf(false) }

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                ExposedDropdownMenuBox(
                    expanded = voiceExpanded,
                    onExpandedChange = { voiceExpanded = it },
                    modifier = Modifier.weight(1f)
                ) {
                    OutlinedTextField(
                        value = selectedVoice?.name ?: currentVoice?.name ?: "No voice configured",
                        onValueChange = {},
                        readOnly = true,
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = voiceExpanded) },
                        modifier = Modifier.menuAnchor(ExposedDropdownMenuAnchorType.PrimaryNotEditable, enabled = true)
                    )
                    ExposedDropdownMenu(
                        expanded = voiceExpanded,
                        onDismissRequest = { voiceExpanded = false }
                    ) {
                        voices.forEach { voice ->
                            DropdownMenuItem(
                                text = {
                                    Column {
                                        Text(voice.name)
                                        voice.description?.let { desc ->
                                            Text(
                                                text = desc,
                                                style = MaterialTheme.typography.bodySmall,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant
                                            )
                                        }
                                    }
                                },
                                onClick = {
                                    onVoiceSelected(voice)
                                    voiceExpanded = false
                                }
                            )
                        }
                    }
                }

                // Save button
                val hasChanges = selectedVoice != null && selectedVoice.id != currentVoice?.id
                Button(
                    onClick = onSaveVoice,
                    enabled = hasChanges && !isSavingVoice
                ) {
                    if (isSavingVoice) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.onPrimary
                        )
                    } else {
                        Text("Save")
                    }
                }
            }

            // Error message
            voiceSaveError?.let { error ->
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = error,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
        }

        Spacer(modifier = Modifier.height(32.dp))
        HorizontalDivider()
        Spacer(modifier = Modifier.height(16.dp))

        // Connection status
        Text(
            text = "Connection Status",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onBackground
        )

        Spacer(modifier = Modifier.height(8.dp))

        val statusText = when (connectionState) {
            ConnectionState.DISCONNECTED -> "Disconnected"
            ConnectionState.CONNECTING -> "Connecting..."
            ConnectionState.CONNECTED -> "Connected"
            ConnectionState.ERROR -> "Error"
        }

        val statusColor = when (connectionState) {
            ConnectionState.DISCONNECTED -> MaterialTheme.colorScheme.onSurfaceVariant
            ConnectionState.CONNECTING -> MaterialTheme.colorScheme.tertiary
            ConnectionState.CONNECTED -> MaterialTheme.colorScheme.primary
            ConnectionState.ERROR -> MaterialTheme.colorScheme.error
        }

        Text(
            text = statusText,
            style = MaterialTheme.typography.bodyMedium,
            color = statusColor
        )
    }
}
