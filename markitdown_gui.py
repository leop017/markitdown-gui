"""MarkItDown GUI – thin entry point.

All logic lives in the ``mdgui`` package.  This file exists only so that
PyInstaller can use ``markitdown_gui.py`` as the analysis entry script and
so that the historical ``python markitdown_gui.py`` invocation keeps working.
"""
from mdgui.app import main

if __name__ == "__main__":
    main()
