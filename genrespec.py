"""Provide wrapper for interacting with genre spec component of config."""

from common.utilities import debug
from common.utilities import config


class GenreSpec():
    def __iter__(self):
        return iter(config.genre_spec)

    def all_keys(self, genre: str) -> list:
        # Return the sum of keys for primary and secondary.
        return sum(config.genre_spec[genre].values(), start=[])

    def primary_keys(self, genre: str) -> list:
        return config.genre_spec[genre]['primary']

    def rename_genre(self, old_genre: str, new_genre: str):
        with config.modify('genre spec') as spec:
            new_genre_spec = \
                    {(genre if genre != old_genre else new_genre): spec
                        for genre, spec in spec.items()}
            # Reassigning to spec decouples this dict from the one sent
            # by the context manager, so modify spec in place.
            spec.clear()
            spec.update(new_genre_spec)

    def reorder_genres(self, new_order: list):
        with config.modify('genre spec') as spec:
            new_genre_spec = {key: spec[key] for key in new_order}
            spec.clear()
            spec.update(new_genre_spec)

    def add_genre(self, new_genre, primary_key):
        with config.modify('genre spec') as spec:
            spec[new_genre] = {'primary': [primary_key],
                    'secondary': []}

    def delete_genre(self, old_genre: str):
        with config.modify('genre spec') as spec:
            del spec[old_genre]


genre_spec = GenreSpec()

