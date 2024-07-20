import pickle
import re
from itertools import zip_longest

from common.utilities import debug
from common.utilities import Value

DEFAULT_GENRE = 'New_genre'
DEFAULT_KEY = 'new_key'
#DEFAULT_VALUE = lambda new_key: f'*{new_key}*'
DEFAULT_VALUE = lambda new_key: ''
NULLVALUE = ('',)

OMIT_FORENAMES = (r'(?u)[\w\s&,-]+\s+(?!I{2,3}$|[JS]r\.*$)', '')

operations = {}

def operation(f):
    operation_name = f.__name__
    operations[operation_name] = f
    return f

def abbrev(name):
    if name == NULLVALUE:
        return name
    pattern, replacement = OMIT_FORENAMES
    return re.sub(pattern, replacement, name)

@operation
def add_key(short_metadata, recording_shelf, uuid, work_num, fo_tmp,
        local_vars):
    new_key = local_vars['new_key']
    is_primary = local_vars['is_primary']

    recording_tuple = recording_shelf[uuid]
    work = recording_tuple.works[work_num]

    # If new_key is in nonce, use its value. Otherwise, assign
    # a default value. If I use a value from nonce, I need to
    # remove it from nonce.
    nonce_dict = dict(recording_tuple.nonce)
    if new_key in nonce_dict:
        new_val = nonce_dict[new_key]
        del nonce_dict[new_key]
        work = work._replace(nonce=list(nonce_dict.items()))
    elif is_primary:
        new_val = (DEFAULT_VALUE(new_key),)
    else:
        new_val = NULLVALUE
    work.metadata.append(new_val)

    recording_shelf[uuid] = recording_tuple

    if is_primary:
        short_metadata.append((abbrev(new_val[0]),))
        pickle.dump((tuple(short_metadata), uuid, work_num), fo_tmp)

@operation
def delete_key(short_metadata, recording_shelf, uuid, work_num, fo_tmp,
        local_vars):
    del_key = local_vars['del_key']
    is_primary = local_vars['is_primary']
    all_keys = local_vars['all_keys']

    recording_tuple = recording_shelf[uuid]
    work = recording_tuple.works[work_num]

    # Remove the value corresponding to del_key from metadata
    # and move it to nonce.
    long_metadata = work.metadata
    value_dict = dict(zip(all_keys, long_metadata))
    if del_val := value_dict.pop(del_key):
        recording_tuple.nonce.append(del_val)
        work = work._replace(metadata=list(value_dict.values()))

    recording_shelf[uuid] = recording_tuple

    if is_primary:
        key_val = zip(all_keys, short_metadata)
        short_metadata = \
                [v for k, v in key_val if k != del_key]
        pickle.dump((tuple(short_metadata), uuid, work_num), fo_tmp)

@operation
def rename_key(short_metadata, recording_shelf, uuid, work_num, fo_tmp,
        local_vars):
    new_key = local_vars['new_key']
    old_key = local_vars['old_key']
    all_keys = local_vars['all_keys']

    recording_tuple = recording_shelf[uuid]
    work = recording_tuple.works[work_num]
    long_metadata = work.metadata
    value_list = list(map(Value._make,
            zip_longest(long_metadata, short_metadata,
                fillvalue=NULLVALUE)))
    new_metadata_list = []

    # If there is a nonce with the same key, remove the nonce
    # from recording_tuple.nonce and attach its value to new_key.
    nonce_dict = dict(work.nonce)
    nonce_long = nonce_dict.get(new_key, NULLVALUE)
    if nonce_long != NULLVALUE:
        del nonce_dict[new_key]
        work = work._replace(nonce=list(nonce_dict.items()))

    for key, val in zip(all_keys, value_list):
        if key == old_key:
            # We already replaced old_key with new_key above. Now
            # derive a value to assign to new_key.
            if val.long == (DEFAULT_VALUE(old_key),):
                # old_key was newly created, so it was assigned
                # a default value. If there happens to be a nonce
                # with new_key, then its value is preferable to
                # a default value. Otherwise, change the value
                # to the default value for new_key.
                new_long = nonce_long if nonce_long != NULLVALUE \
                        else (DEFAULT_VALUE(new_key),)
                new_val = Value(new_long, (abbrev(new_long[0]),))
            else:
                # old_key was not newly created, so it has a real
                # value or NULLVALUE. If new_key also happens to
                # be a nonce, preserve the nonce value by adding
                # it to the value for old_key.
                nonce_val = Value(nonce_long, (abbrev(nonce_long[0]),))
                new_val = val + nonce_val
        else:
            # key != old_key, so just copy over the value.
            new_val = val
        new_metadata_list.append(new_val)

    new_long_metadata_tuple, new_short_metadata_tuple = \
            zip(*new_metadata_list)
    new_short_metadata_list = \
            list(new_short_metadata_tuple[:len(short_metadata)])

    work = work._replace(metadata=list(new_long_metadata_tuple))
    recording_shelf[uuid] = recording_tuple
    pickle.dump((tuple(new_short_metadata_list), uuid, work_num), fo_tmp)

@operation
def rearrange_primary(short_metadata, recording_shelf, uuid, work_num,
        fo_tmp, local_vars):
    from_index = local_vars['from_index']
    insert_index = local_vars['insert_index']

    recording_tuple = recording_shelf[uuid]
    work = recording_tuple.works[work_num]
    long_metadata = work.metadata

    value = long_metadata.pop(from_index)
    long_metadata.insert(insert_index, value)

    value = short_metadata.pop(from_index)
    short_metadata.insert(insert_index, value)

    work = work._replace(metadata=long_metadata)
    recording_shelf[uuid] = recording_tuple

    pickle.dump((tuple(short_metadata), uuid, work_num), fo_tmp)

@operation
def rearrange_secondary(short_metadata, recording_shelf, uuid, work_num,
        fo_tmp, local_vars):
    from_index = local_vars['from_index'] + len(local_vars['primary_keys'])
    insert_index = local_vars['insert_index'] \
            + len(local_vars['primary_keys'])

    recording_tuple = recording_shelf[uuid]
    work = recording_tuple.works[work_num]
    long_metadata = work.metadata

    value = long_metadata.pop(from_index)
    long_metadata.insert(insert_index, value)

    work._replace(metadata=long_metadata)
    recording_shelf[uuid] = recording_tuple

@operation
def demote_primary(short_metadata, recording_shelf, uuid, work_num, fo_tmp,
        local_vars):
    from_index = local_vars['from_index']
    insert_index = local_vars['insert_index']

    recording_tuple = recording_shelf[uuid]
    work = recording_tuple.works[work_num]
    long_metadata = work.metadata

    value = long_metadata.pop(from_index)
    long_metadata.insert(insert_index, value)

    del short_metadata[from_index]

    work = work._replace(metadata=long_metadata)
    recording_shelf[uuid] = recording_tuple

    pickle.dump((tuple(short_metadata), uuid, work_num), fo_tmp)

@operation
def promote_secondary(short_metadata, recording_shelf, uuid, work_num,
        fo_tmp, local_vars):
    from_index = local_vars['from_index']
    insert_index = local_vars['insert_index']

    recording_tuple = recording_shelf[uuid]
    work = recording_tuple.works[work_num]
    long_metadata = work.metadata

    value = long_metadata.pop(from_index)
    long_metadata.insert(insert_index, value)

    short_value = tuple(abbrev(v) for v in value)
    short_metadata.insert(insert_index, short_value)

    work = work._replace(metadata=long_metadata)
    recording_shelf[uuid] = recording_tuple

    pickle.dump((tuple(short_metadata), uuid, work_num), fo_tmp)

