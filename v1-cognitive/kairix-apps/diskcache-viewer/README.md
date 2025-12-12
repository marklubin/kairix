# Kairix Notebook Viewer

A terminal user interface (TUI) for viewing and editing kairix persona notebook entries stored in diskcache.

## Features

- **IDE-style Interface**: Split-pane layout with explorer (left) and viewer/editor (right)
- **Browse Notes**: View all notebook entries in an organized list
- **Markdown Rendering**: View notes with rich markdown formatting
- **Edit Mode**: Edit note content in a text editor
- **Metadata Display**: See creation date, modification date, and tags for each note
- **Cache Validation**: Ensures you're working with a valid kairix cache structure

## Installation

The package is installed as part of the kairix-apps workspace. From the `kairix-apps` directory:

```bash
# The diskcache-viewer is already installed when you install kairix-apps
cd kairix-apps/diskcache-viewer
```

## Usage

### Basic Usage

Launch the viewer from the `diskcache-viewer` directory:

```bash
# Using the default cache location (../. cache)
source ../.venv/bin/activate
python -m src

# Or specify a custom cache path
python -m src --cache-path /path/to/.cache
```

### Navigation

- **Explorer Pane** (left): List of all notes
  - Use arrow keys to navigate
  - Press Enter to select a note

- **Viewer Pane** (right): Display and edit notes
  - View notes with rendered markdown or as plain text
  - Switch between view and edit modes
  - Save changes back to the cache

### Keyboard Shortcuts

- `q` - Quit the application
- `r` - Refresh the note list
- Use tab to switch between panes

### Buttons

- **Edit** - Switch to edit mode (allows modifying note content)
- **View** - Switch back to view mode (renders markdown)
- **Save** - Save changes to the cache (only in edit mode)

## Architecture

### Directory Structure

```
diskcache-viewer/
├── src/
│   ├── app.py              # Main Textual application
│   ├── cache_reader.py     # Cache validation and data access
│   └── widgets/
│       ├── explorer.py     # Note list sidebar widget
│       └── viewer.py       # Note viewer/editor widget
├── tests/
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── conftest.py         # Shared test fixtures
└── pyproject.toml          # Package configuration
```

### Components

#### cache_reader.py

- **NotebookCache**: Main interface for reading/writing notebook entries
  - Validates cache structure (ensures it's a valid kairix cache)
  - Provides CRUD operations for notes
  - Handles Note object serialization/deserialization

- **Note**: Data model for notebook entries
  - `title`: Note title (str)
  - `created_at`: Creation timestamp (datetime)
  - `modified_at`: Last modification timestamp (Optional[datetime])
  - `content`: Note content in markdown format (str)
  - `tags`: Set of tags (set[str])

#### widgets/explorer.py

- **ExplorerPane**: Left sidebar showing list of notes
  - Displays note titles with metadata
  - Sorted alphabetically
  - Sends `NoteSelected` message when user selects a note

#### widgets/viewer.py

- **ViewerPane**: Right pane for viewing/editing notes
  - Two modes: view (rendered markdown) and edit (plain text)
  - Displays note metadata (title, dates, tags)
  - Allows saving changes back to cache

## Cache Structure

The viewer expects the following cache directory structure:

```
.cache/
├── index/
│   └── persona_notebook/
│       └── cache.db        # SQLite database with notebook entries
└── [other fanout cache shards]
```

### Validation

The viewer performs the following validations on startup:

1. Cache path exists and is a directory
2. `index/` subdirectory exists
3. `index/persona_notebook/` subdirectory exists
4. `index/persona_notebook/cache.db` file exists

If any validation fails, the app exits with an error message.

## Development

### Running Tests

```bash
# Activate the virtual environment
source ../.venv/bin/activate

# Run all tests
pytest

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### Test Structure

- **Unit Tests** (`tests/unit/test_cache_reader.py`):
  - Cache validation logic
  - CRUD operations
  - Context manager functionality

- **Integration Tests** (`tests/integration/test_full_app.py`):
  - Full application flow
  - UI interactions
  - Data persistence

- **Test Fixtures** (`tests/conftest.py`):
  - `temp_cache_dir`: Creates a temporary cache with test data
  - `invalid_cache_dir`: Creates an invalid cache for error testing
  - `empty_cache_dir`: Creates a cache without notebook index

### Adding New Features

1. **New cache operations**: Add to `cache_reader.py`
2. **New UI elements**: Add to appropriate widget in `widgets/`
3. **New actions**: Add to `app.py` with keyboard bindings
4. **Always add tests**: Unit tests for logic, integration tests for flow

## Troubleshooting

### Error: "No 'index' directory found"

The cache path doesn't point to a valid kairix cache. Ensure you're pointing to the `.cache` directory created by kairix-apps.

### Error: "No 'persona_notebook' index found"

The cache exists but doesn't contain notebook data. This is expected if no notes have been created yet.

### App won't start

1. Ensure you've activated the virtual environment
2. Check that all dependencies are installed: `pip list | grep textual`
3. Verify the cache path is correct

### Notes don't update

Make sure to click the "Save" button after editing. The app only writes to the cache when you explicitly save.

## Technical Details

### Data Storage

Notes are stored in a diskcache Index, which uses SQLite for metadata and pickle for object serialization. The `_CacheNote` class matches the structure of kairix's Note class to ensure compatibility.

### Concurrency

The viewer reads and writes to the same cache as the kairix server. Changes made in the viewer are immediately visible to the server and vice versa (after refresh).

### Performance

- Cache reads are lazy-loaded
- Notes are only unpickled when accessed
- Markdown rendering is on-demand

## License

Part of the Kairix project.
