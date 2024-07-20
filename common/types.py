from typing import NamedTuple

# Named tuples:
# RecordingTuple.tracks is the list of all tracks on the CD.
# Note that all values in props are str, but they are embedded in a tuple
class RecordingTuple(NamedTuple):
    works: object       # {0: WorkTuple, ...}
    tracks: object      # [TrackTuple, ...]
    props: object       # [(str, (str, ...)), ...] (key, values)
    discids: object     # [str, ...]
    uuid: str

# WorkTuple.tracks is the list of all tracks in the work.
# Each (str, ...) is a namegroup. An empty namegroup is ('',).
class WorkTuple(NamedTuple):
    genre: str
    metadata: object    # [(str, ...), (str, ...), ...] (just values)
    nonce: object       # [(str, (str, ...)), ...] (key, values)
    tracks: object      # [(track_id1), ...]
    trackgroups: object # [(str, [(disc_num, track_num), ...]), ...]

class TrackTuple(NamedTuple):
    disc_num: int
    track_num: int
    title: str
    duration: float = 0.0
    metadata: object = [] # [(str, [str])]

    @property
    def track_id(self):
        return (self.disc_num, self.track_num)

    @classmethod
    def _convert(cls, grouptuple):
        return cls(-1, -1, grouptuple.title, 0.0, grouptuple.metadata)

    def is_group(self):
        return (self.disc_num, self.track_num) == (-1, -1)

    def __str__(self):
        return f'{self.disc_num} {self.track_num:02d}'

    def __eq__(self, other):
        return self.track_id == other.track_id

