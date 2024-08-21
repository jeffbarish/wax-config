from pathlib import Path

DATABASE = 'recordings'
METADATA = Path(DATABASE, 'metadata')
CONFIG = Path(METADATA, 'config')
COMPLETERS = Path(METADATA, 'completers')
SHORT = Path(METADATA, 'short')
LONG = Path(METADATA, 'long')

DOCUMENTS = Path(DATABASE, 'documents')
IMAGES = Path(DATABASE, 'images')
SOUND = Path(DATABASE, 'sound')

PROPS_REC = ['source', 'codec', 'sample rate', 'resolution', 'date created']
PROPS_WRK = ['times played', 'date played']

NOEXPAND = (False, False, 0)

MAIN_WINDOW_SIZE = (800-341-6, 540)

METADATA_CLASSES = ('primary', 'secondary')

