import shutil
from pathlib import Path

from common.constants import DATABASE
from common.constants import METADATA

CHECKPOINTS = Path(DATABASE, '.checkpoints')

def push_checkpoint(comment):
    n_checkpoints = len(list(CHECKPOINTS.iterdir()))
    new_checkpoint = Path(CHECKPOINTS, str(n_checkpoints + 1))
    shutil.copytree(METADATA, new_checkpoint)

    # Write comment into new checkpoint.
    Path(new_checkpoint, '.comment').write_text(comment)

def pop_checkpoint():
    try:
        n_checkpoints = len(list(CHECKPOINTS.iterdir()))
    except ValueError:
        # .checkpoints directory is empty (should never happen because the
        # undo button should have been disabled).
        return

    # Replace METADATA with the last checkpoint.
    shutil.rmtree(METADATA)
    Path(CHECKPOINTS, str(n_checkpoints)).rename(METADATA)

    # We do not need the comment anymore for what used to be the last
    # checkpoint.
    Path(METADATA, '.comment').unlink()

    # Update the comment.
    comment = update_comment()
    return comment

def remove_checkpoints():
    if CHECKPOINTS.is_dir():
        shutil.rmtree(CHECKPOINTS)
    CHECKPOINTS.mkdir()

def update_comment():
    if CHECKPOINTS.is_dir():
        if n_checkpoints := len(list(CHECKPOINTS.iterdir())):
            last_checkpoint = Path(CHECKPOINTS, str(n_checkpoints))
            comment = Path(last_checkpoint, '.comment').read_text()
        else:
            comment = ''
    else:
        CHECKPOINTS.mkdir()
        comment = ''
    return comment

def make_comment(*args):
    # args has alternating text and data.
    args_iter = iter(args)
    markup = []
    while True:
        try:
            markup.append(next(args_iter))

            # Use green color for data.
            spanner = '<span foreground="#009185">{}</span>'
            markup.append(spanner.format(next(args_iter)))
        except StopIteration:
            break
    return ' '.join(markup)

