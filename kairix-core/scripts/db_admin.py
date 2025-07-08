#!/usr/bin/env python3
"""SQLite admin TUI with database initialization."""
import sqlite3
import os
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Input, Static
from textual.binding import Binding

DEFAULT_ENTITIES = [
    ('person', 'Human entity - individuals mentioned or interacted with'),
    ('location', 'Physical or virtual locations'),
    ('organization', 'Companies, groups, institutions'),
    ('event', 'Temporal occurrences or happenings'),
    ('concept', 'Abstract ideas or themes'),
    ('object', 'Physical items or artifacts'),
    ('date', 'Specific dates or time periods'),
    ('url', 'Web addresses and links'),
    ('emotion', 'Feelings or emotional states'),
    ('skill', 'Abilities or competencies')
]

DEFAULT_LINKAGES = [
    ('related_to', 'General relationship between entities'),
    ('located_at', 'Entity is at a location'),
    ('works_for', 'Employment relationship'),
    ('knows', 'Personal acquaintance'),
    ('participates_in', 'Participation in event'),
    ('owns', 'Ownership relationship'),
    ('created_by', 'Creation relationship'),
    ('mentioned_with', 'Co-occurrence in context'),
    ('causes', 'Causal relationship'),
    ('precedes', 'Temporal ordering')
]

class DBAdmin(App):
    CSS = """
    DataTable {
        height: 1fr;
        border: solid green;
        overflow-x: auto;
        overflow-y: scroll;
    }
    Input {
        dock: bottom;
        height: 3;
        border: solid blue;
    }
    #keys {
        height: 3;
        padding: 1;
        background: $surface;
        border: solid yellow;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("t", "tables", "Tables"),
        Binding("s", "schema", "Schema"),
        Binding("e", "entities", "Entities"),
        Binding("l", "linkages", "Linkages"),
        Binding("i", "init_db", "Init DB"),
        Binding("c", "copy_enums", "Copy"),
        Binding("m", "migrate", "Migrate"),
        Binding("/", "focus_sql", "SQL"),
        Binding("escape", "unfocus", "Clear", show=False),
        Binding("ctrl+c", "copy_selection", "Copy", show=False),
        Binding("ctrl+v", "paste_clipboard", "Paste", show=False),
    ]
    
    def __init__(self, db_path="kairix.db"):
        super().__init__()
        self.db_path = Path(db_path).resolve()
        self.conn = None
        
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("[b]Keys:[/b] [q]uit [t]ables [s]chema [e]ntities [l]inkages [i]nit [c]opy [m]igrate [/]sql", id="keys")
        yield DataTable()
        yield Input(placeholder="SQL query, INIT:user, COPY:target.db, or MIGRATE:neo4j_url")
        yield Footer()
        
    def on_mount(self) -> None:
        self.table = self.query_one(DataTable)
        self.input = self.query_one(Input)
        self.connect_db()
        
    def connect_db(self) -> None:
        """Connect to database, create if doesn't exist."""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            self.action_tables()
        except Exception as e:
            self.show_error(f"Connection failed: {e}")
            
    def action_tables(self) -> None:
        """Show all tables."""
        self.run_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        
    def action_schema(self) -> None:
        """Show full schema."""
        try:
            cursor = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            schema_rows = []
            for table in cursor:
                info = self.conn.execute(f"PRAGMA table_info('{table[0]}')").fetchall()
                for col in info:
                    schema_rows.append([table[0], col[1], col[2], col[5] == 1 and "PK" or ""])
            self.show_results(["table", "column", "type", "key"], schema_rows)
        except Exception as e:
            self.show_error(str(e))
            
    def action_entities(self) -> None:
        """Show entity types."""
        self.run_query("SELECT name, description FROM entity_class ORDER BY name")
        
    def action_linkages(self) -> None:
        """Show linkage types."""
        self.run_query("SELECT name, description FROM linkage_type ORDER BY name")
        
    def action_init_db(self) -> None:
        """Initialize database."""
        self.input.value = "INIT:username"
        self.input.focus()
        
    def action_copy_enums(self) -> None:
        """Copy enums to another database."""
        self.input.value = "COPY:target.db"
        self.input.focus()
        
    def action_migrate(self) -> None:
        """Migrate from Neo4j."""
        self.input.value = "MIGRATE:bolt://neo4j:password@localhost:7687"
        self.input.focus()
        
    def action_focus_sql(self) -> None:
        """Focus SQL input."""
        self.input.focus()
        
    def action_unfocus(self) -> None:
        """Clear input and unfocus."""
        self.input.clear()
        self.table.focus()
        
    def action_copy_selection(self) -> None:
        """Copy selected text or table data to clipboard."""
        import pyperclip
        try:
            # Get selected text from focused widget
            focused = self.focused
            if focused == self.table:
                # For DataTable, copy all visible data
                data = []
                if self.table.columns:
                    # Add headers
                    headers = [col.label.plain for col in self.table.columns.values()]
                    data.append('\t'.join(headers))
                    
                    # Add rows
                    for row_key in self.table.rows:
                        row_data = []
                        for col_key in self.table.columns:
                            cell = self.table.get_cell(row_key, col_key)
                            row_data.append(str(cell))
                        data.append('\t'.join(row_data))
                
                text = '\n'.join(data)
                pyperclip.copy(text)
                self.notify("Copied table data to clipboard", severity="information")
            elif focused == self.input:
                # For input, copy current value
                if self.input.value:
                    pyperclip.copy(self.input.value)
                    self.notify("Copied input to clipboard", severity="information")
        except ImportError:
            self.notify("pyperclip not installed - install with: uv add pyperclip", severity="warning")
        except Exception as e:
            self.notify(f"Copy failed: {e}", severity="error")
            
    def action_paste_clipboard(self) -> None:
        """Paste from clipboard to input."""
        import pyperclip
        try:
            text = pyperclip.paste()
            if text and self.focused == self.input:
                # Insert at cursor position
                self.input.insert_text_at_cursor(text)
                self.notify("Pasted from clipboard", severity="information")
        except ImportError:
            self.notify("pyperclip not installed - install with: uv add pyperclip", severity="warning")
        except Exception as e:
            self.notify(f"Paste failed: {e}", severity="error")
        
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        cmd = event.value.strip()
        if not cmd:
            return
            
        if cmd.startswith("INIT:"):
            username = cmd.split(":", 1)[1]
            self.init_database(username)
        elif cmd.startswith("COPY:"):
            target = cmd.split(":", 1)[1]
            self.copy_enums(target)
        elif cmd.startswith("MIGRATE:"):
            neo4j_url = cmd.split(":", 1)[1]
            # Re-add the protocol
            if not neo4j_url.startswith("bolt://"):
                neo4j_url = "bolt://" + neo4j_url
            self.migrate_from_neo4j(neo4j_url)
        elif cmd.upper().startswith(("INSERT", "UPDATE", "DELETE")):
            self.execute_write(cmd)
        else:
            self.run_query(cmd)
            
        self.input.clear()
        
    def run_query(self, query: str) -> None:
        """Execute and display query."""
        try:
            cursor = self.conn.execute(query)
            rows = cursor.fetchall()
            if rows:
                columns = [desc[0] for desc in cursor.description]
                self.show_results(columns, [[str(row[i]) for i in range(len(columns))] for row in rows])
            else:
                self.show_results(["result"], [["No results"]])
        except Exception as e:
            self.show_error(str(e))
            
    def execute_write(self, query: str) -> None:
        """Execute write query."""
        try:
            self.conn.execute(query)
            self.conn.commit()
            self.show_results(["result"], [[f"{self.conn.total_changes} row(s) affected"]])
        except Exception as e:
            self.conn.rollback()
            self.show_error(str(e))
            
    def show_results(self, columns: list, rows: list) -> None:
        """Display results in table."""
        if not hasattr(self, 'table'):
            # Not in TUI mode, just print
            print(f"Results: {columns}")
            for row in rows:
                print(f"  {row}")
            return
        self.table.clear(columns=True)
        self.table.add_columns(*columns)
        for row in rows:
            self.table.add_row(*row)
            
    def show_error(self, error: str) -> None:
        """Display error."""
        if not hasattr(self, 'table'):
            # Not in TUI mode, just print
            print(f"Error: {error}")
            return
        self.table.clear(columns=True)
        self.table.add_column("Error Details", width=100)
        
        # Split error message by lines to display properly
        for line in str(error).split('\n'):
            if line.strip():  # Only add non-empty lines
                self.table.add_row(line)
        
    def init_database(self, username: str) -> None:
        """Initialize a new user database."""
        db_dir = Path.home() / "kairix" / ".sqlite"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / f"{username}.db"
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Create schema
            cursor.executescript('''
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS entity_class (
                name TEXT PRIMARY KEY,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS linkage_type (
                name TEXT PRIMARY KEY,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                semantic_id TEXT NOT NULL,
                entity_class TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_class) REFERENCES entity_class(name)
            );
            
            CREATE TABLE IF NOT EXISTS semantic_linkages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                linkage_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (linkage_type) REFERENCES linkage_type(name)
            );
            
            CREATE TABLE IF NOT EXISTS memory_shards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT UNIQUE,
                contents TEXT NOT NULL,
                embedding_type TEXT,
                embedding BLOB,
                agent_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            );
            
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id),
                UNIQUE(thread_id, sequence_number)
            );
            ''')
            
            # Insert defaults
            for name, desc in DEFAULT_ENTITIES:
                cursor.execute("INSERT OR IGNORE INTO entity_class (name, description) VALUES (?, ?)", (name, desc))
            
            for name, desc in DEFAULT_LINKAGES:
                cursor.execute("INSERT OR IGNORE INTO linkage_type (name, description) VALUES (?, ?)", (name, desc))
                
            cursor.execute("INSERT OR IGNORE INTO agents (name) VALUES ('default')")
            
            conn.commit()
            conn.close()
            
            self.show_results(["result"], [[f"Created database: {db_path}"]])
            
        except Exception as e:
            self.show_error(f"Init failed: {e}")
            
    def copy_enums(self, target_path: str) -> None:
        """Copy enum tables to target database."""
        try:
            # Handle relative paths
            if not os.path.isabs(target_path):
                target_path = str(Path.cwd() / target_path)
                
            target_conn = sqlite3.connect(target_path)
            
            # Copy entity_class
            entities = self.conn.execute("SELECT name, description FROM entity_class").fetchall()
            for entity in entities:
                target_conn.execute(
                    "INSERT OR IGNORE INTO entity_class (name, description) VALUES (?, ?)",
                    (entity[0], entity[1])
                )
            
            # Copy linkage_type
            linkages = self.conn.execute("SELECT name, description FROM linkage_type").fetchall()
            for linkage in linkages:
                target_conn.execute(
                    "INSERT OR IGNORE INTO linkage_type (name, description) VALUES (?, ?)",
                    (linkage[0], linkage[1])
                )
            
            target_conn.commit()
            target_conn.close()
            
            count = len(entities) + len(linkages)
            self.show_results(["result"], [[f"Copied {count} enum entries to {target_path}"]])
            
        except Exception as e:
            self.show_error(f"Copy failed: {e}")
            
    def migrate_from_neo4j(self, neo4j_url: str) -> None:
        """Run Neo4j to SQLite migration."""
        try:
            self.show_results(["status"], [["Starting migration from Neo4j..."]])
            
            # Import here to avoid dependency issues
            from kairix_core.database.neo4j_to_sqlite import Neo4jToSQLiteConverter
            from kairix_core.runtime.storage import StorageRuntime
            
            # Create storage runtime with the current database path
            storage = StorageRuntime(db_path=str(self.db_path))  # VSS is now always enabled
            
            # Show where data will be migrated to
            self.show_results(["info"], [[f"Migrating data to: {self.db_path}"]])
            
            # Create converter
            converter = Neo4jToSQLiteConverter(neo4j_url, storage)
            
            # Run migration steps with progress updates
            steps = [
                ("agents", converter._convert_agents),
                ("concepts -> entities", converter._convert_concepts_to_entities),
                ("semantic linkages", converter._convert_semantic_linkages),
                ("source documents", converter._convert_source_documents),
                ("summaries", converter._convert_summaries),
                ("memory shards", converter._convert_memory_shards),
                ("conversation history", converter._convert_conversation_history),
            ]
            
            results = []
            errors = []
            for step_name, step_func in steps:
                try:
                    step_func()
                    results.append([f"✓ Migrated {step_name}"])
                except Exception as e:
                    import traceback
                    # Get full traceback with line numbers
                    tb_lines = traceback.format_exc().strip().split('\n')
                    results.append([f"✗ Failed {step_name}: {str(e)}"])
                    
                    # Store error for detailed display
                    errors.append(f"\n{'='*80}\nERROR IN: {step_name}\n{'='*80}")
                    errors.extend(tb_lines)
                    
            results.append(["", "Migration complete!"])
            self.show_results(["Migration Results"], results)
            
            # If there were errors, show them in detail
            if errors:
                # Show all errors in a single error display
                full_error_text = '\n'.join(errors)
                self.show_error(full_error_text)
            else:
                # Refresh tables view only if successful
                self.action_tables()
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.show_error(f"Migration failed: {e}\n\nFull traceback:\n{error_details}")

def main():
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "kairix.db"
    app = DBAdmin(db_path)
    app.run()

if __name__ == "__main__":
    main()