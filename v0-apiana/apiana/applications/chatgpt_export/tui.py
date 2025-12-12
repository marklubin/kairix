from textual.app import App
from textual.errors import RenderError
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    DataTable,
    DirectoryTree,
    LoadingIndicator,
    Static,
    TextArea,
)


class FilteredDirectoryTree(DirectoryTree):
    @classmethod
    def hidden_file_filter(cls, path):
        """Filter function to exclude hidden files and directories."""
        return not path.name.startswith(".")

    @classmethod
    def all_files_filter(cls, path):
        """Filter function to include all files."""
        return path.is_file()

    def __init__(self, path, fn):
        super().__init__(path)
        self.fn = fn

    def filter_paths(self, paths):
        return [path for path in paths if not self.fn(path)]


class FilePicker(Widget):
    path = reactive("../")

    def __init__(self, user_prompt, on_file_selected):
        super().__init__()
        self.user_prompt = user_prompt
        self.on_file_selected = on_file_selected

    def compose(self):
        yield Static(self.user_prompt)
        yield FilteredDirectoryTree(self.path, FilteredDirectoryTree.hidden_file_filter)

    def on_directory_tree_directory_selected(self, event):
        self.path = event.path

    def on_directory_tree_file_selected(self, event):
        file_path = event.path
        if file_path:
            self.on_file_selected(file_path)


class ChatGPTExportProcessor(App):
    state = reactive("new")
    input_filename = reactive(None)
    validated_convos = reactive([])
    system_prompt_filename = reactive(None)
    prompt_text = reactive(None)

    def on_mount(self):
        self.theme = "solarized-light"

    def compose(self):
        if self.state == "new":
            yield FilePicker(
                "Select a file to process ChatGPT conversations:",
                self.on_file_selection_complete,
            )
        elif self.state == "loading":
            yield LoadingIndicator("Validating Schema...")
        elif self.state == "loaded":
            yield Static(f"Processed {len(self.validated_convos)} conversations.")
            dt = DataTable()
            self.load_table(dt)
            yield dt
            yield Static("Press ENTER to select summarization prompt.")
        elif self.state == "prompt_selection":
            yield FilePicker(
                "Select a summarization system prompt file:",
                self.on_prompt_file_selection_complete,
            )
        elif self.state == "comfirming":
            yield Static(
                f"Ready to summarize {len(self.validated_convos)} conversations selected Prompt."
            )
            yield TextArea(text=self.prompt_text)

    def key_enter(self):
        if self.state == "loaded":
            self.change_workflow_state("prompt_selection")

    def on_prompt_file_selection_complete(self, file_path: str) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                self.prompt_text = file.read()
                self.change_workflow_state("comfirming")
        except Exception as e:
            print(f"❌ Error reading prompt file: {e}")
            self.log.error(f"Error reading prompt file: {e}")
            raise RenderError(f"Error reading prompt file: {e}", e)

    def on_file_selection_complete(self, file_path: str) -> None:
        self.input_filename = file_path
        self.change_workflow_state("loading")
        # self.import_file(self.input_filename)
        self.change_workflow_state("loaded")

    def load_table(self, data_table: DataTable) -> None:
        data_table.clear()
        data_table.add_column("Title")
        data_table.add_column("Number of Messages")

        data_table.add_rows(
            [(convo.title, len(convo.messages)) for convo in self.validated_convos]
        )

    def change_workflow_state(self, new_state: str) -> None:
        self.state = new_state
        self.refresh(recompose=True)


def main():
    ChatGPTExportProcessor().run()


if __name__ == "__main__":
    main()
