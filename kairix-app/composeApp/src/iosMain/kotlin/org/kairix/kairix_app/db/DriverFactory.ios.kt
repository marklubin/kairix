package org.kairix.kairix_app.db

import app.cash.sqldelight.db.SqlDriver
import app.cash.sqldelight.driver.native.NativeSqliteDriver

/**
 * iOS implementation of DriverFactory.
 * Uses NativeSqliteDriver which wraps iOS's native SQLite.
 */
actual class DriverFactory {
    actual fun createDriver(): SqlDriver {
        return NativeSqliteDriver(KairixDatabase.Schema, "kairix_events.db")
    }
}