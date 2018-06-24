# -*- coding: utf-8 -*-
import warnings
from .._utils import exhaustible
from .._utils import seekable
from .._utils import file_types
from .get_reader import get_reader
from .temptable import load_data
from .temptable import savepoint


preferred_encoding = 'utf-8'
fallback_encoding = ['latin-1']


def load_csv(cursor, table, csvfile, encoding=None, **kwds):
    """Load *csvfile* and insert data into *table*."""
    global preferred_encoding
    global fallback_encoding

    default = kwds.get('restval', '')  # Used for default column value.

    if encoding:
        # When an encoding is specified, use it to load *csvfile* or
        # fail if there are errors (no fallback recovery):
        with savepoint(cursor):
            reader = get_reader.from_csv(csvfile, encoding, **kwds)
            load_data(cursor, table, reader, default=default)

        return  # <- EXIT!

    # When the encoding is unspecified, try to load *csvfile* using the
    # preferred encoding and failing that, try the fallback encodings:

    if isinstance(csvfile, file_types) and seekable(csvfile):
        position = csvfile.tell()  # Get current position if
    else:                          # csvfile is file-like and
        position = None            # supports random access.

    try:
        with savepoint(cursor):
            reader = get_reader.from_csv(csvfile, preferred_encoding, **kwds)
            load_data(cursor, table, reader, default=default)

        return  # <- EXIT!

    except UnicodeDecodeError as orig_error:
        if exhaustible(csvfile) and position is None:
            encoding, object_, start, end, reason = orig_error.args  # Unpack args.
            reason = (
                '{0}: unable to load {1!r}, cannot attempt fallback with '
                '{2!r} type: must specify an appropriate text encoding'
            ).format(reason, csvfile, csvfile.__class__.__name__)
            raise UnicodeDecodeError(encoding, object_, start, end, reason)

        if isinstance(fallback_encoding, list):
            fallback_list = fallback_encoding
        else:
            fallback_list = [fallback_encoding]

        for fallback in fallback_list:
            if position is not None:
                csvfile.seek(position)

            try:
                with savepoint(cursor):
                    reader = get_reader.from_csv(csvfile, fallback, **kwds)
                    load_data(cursor, table, reader, default=default)

                msg = (
                    '{0}: loaded {1!r} using fallback {2!r}: specify an '
                    'appropriate text encoding to assure correct operation'
                ).format(orig_error, csvfile, fallback)
                warnings.warn(msg)

                return  # <- EXIT!

            except UnicodeDecodeError:
                pass

        # Note: DO NOT refactor this section using a for-else. I swear...
        encoding, object_, start, end, reason = orig_error.args  # Unpack args.
        reason = (
            '{0}: unable to load {1!r}, fallback recovery unsuccessful: '
            'must specify an appropriate text encoding'
        ).format(reason, csvfile)
        raise UnicodeDecodeError(encoding, object_, start, end, reason)
