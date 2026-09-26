"""nanoPick — find your files by saying what you remember.

The whole idea in one sentence: a person who has lost a file does not remember
a path, they remember *things about it* — "it was a picture, it had receipt in
the name, it was last month". nanoPick turns those words into the file, shows
it right there on the page, and puts it where it needs to go: open it, show the
folder it lives in, send a copy to your project folder, or pack a few of them
into one zip.

It never moves or deletes anything without being asked, and it only ever looks
in the folders you let it look in.
"""

APP_NAME = "nanoPick"
__version__ = "0.1.0"

TAGLINE = "find your files by saying what you remember"

__all__ = ["APP_NAME", "__version__", "TAGLINE"]
