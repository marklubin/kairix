package org.kairix.kairix_app.db

import app.cash.sqldelight.db.SqlDriver

/**
 * Factory for creating platform-specific SQLite drivers.
 * Each platform provides its own actual implementation.
 */
expect class DriverFactory() {
    fun createDriver(): SqlDriver
}