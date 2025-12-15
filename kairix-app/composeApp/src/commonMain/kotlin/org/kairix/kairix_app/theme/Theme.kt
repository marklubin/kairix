package org.kairix.kairix_app.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Base colors from Material Theme Builder
val Primary = Color(0xFFA3FF77)
val Secondary = Color(0xFFB1FFF1)
val Tertiary = Color(0xFFB8FFCB)
val Error = Color(0xFFFF005C)
val Neutral = Color(0xFFDCFFF6)
val NeutralVariant = Color(0xFFD0FFFD)

// Derived colors for full color scheme
val OnPrimary = Color(0xFF003300)
val PrimaryContainer = Color(0xFF7AD94F)
val OnPrimaryContainer = Color(0xFF002200)

val OnSecondary = Color(0xFF003333)
val SecondaryContainer = Color(0xFF88DDD0)
val OnSecondaryContainer = Color(0xFF002222)

val OnTertiary = Color(0xFF003322)
val TertiaryContainer = Color(0xFF8FDDA3)
val OnTertiaryContainer = Color(0xFF002211)

val OnError = Color(0xFFFFFFFF)
val ErrorContainer = Color(0xFFFFDAD9)
val OnErrorContainer = Color(0xFF410002)

val Background = Color(0xFFF8FFF8)
val OnBackground = Color(0xFF1A1C1A)
val Surface = Color(0xFFF8FFF8)
val OnSurface = Color(0xFF1A1C1A)
val SurfaceVariant = Neutral
val OnSurfaceVariant = Color(0xFF404943)
val Outline = Color(0xFF707973)
val OutlineVariant = NeutralVariant

val KairixColorScheme = lightColorScheme(
    primary = Primary,
    onPrimary = OnPrimary,
    primaryContainer = PrimaryContainer,
    onPrimaryContainer = OnPrimaryContainer,
    secondary = Secondary,
    onSecondary = OnSecondary,
    secondaryContainer = SecondaryContainer,
    onSecondaryContainer = OnSecondaryContainer,
    tertiary = Tertiary,
    onTertiary = OnTertiary,
    tertiaryContainer = TertiaryContainer,
    onTertiaryContainer = OnTertiaryContainer,
    error = Error,
    onError = OnError,
    errorContainer = ErrorContainer,
    onErrorContainer = OnErrorContainer,
    background = Background,
    onBackground = OnBackground,
    surface = Surface,
    onSurface = OnSurface,
    surfaceVariant = SurfaceVariant,
    onSurfaceVariant = OnSurfaceVariant,
    outline = Outline,
    outlineVariant = OutlineVariant,
)

@Composable
fun KairixTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = KairixColorScheme,
        content = content
    )
}
