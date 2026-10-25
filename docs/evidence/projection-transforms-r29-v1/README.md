# R29 CPU checkpoint

The index binds 11 original records, with identical before/after data stored once. Each `.gz` contains the exact original bytes; decode with Python `gzip.decompress` and verify both hashes from the index. The first full-run failure and changing-input records are retained. The second full run passed 3550 tests with one skip and unchanged selected inputs. This checkpoint grants no native-game or human acceptance.
