"""Infrastructure layer — adapters implementing the application ports.

The only layer permitted to import third-party packages or touch I/O. It may
import from ``domain`` and ``application``; nothing imports *from* it except the
composition root.
"""
