package org.kairix.kairix_app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import org.kairix.kairix_app.ConnectionState
import org.kairix.kairix_app.Endpoint

/**
 * Settings view for configuring the app.
 */
@Composable
fun SettingsView(
    selectedEndpoint: Endpoint,
    onEndpointSelected: (Endpoint) -> Unit,
    connectionState: ConnectionState,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
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

        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Endpoint.entries.forEach { endpoint ->
                FilterChip(
                    selected = selectedEndpoint == endpoint,
                    onClick = {
                        if (connectionState == ConnectionState.DISCONNECTED) {
                            onEndpointSelected(endpoint)
                        }
                    },
                    label = { Text(endpoint.label) },
                    enabled = connectionState == ConnectionState.DISCONNECTED
                )
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
