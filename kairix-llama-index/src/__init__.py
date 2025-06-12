"""Initialize package with automatic runtime type checking."""

from typeguard import install_import_hook

# Automatically apply typeguard to all modules in this package
install_import_hook("src")

# Re-export your main API here
__all__ = []
