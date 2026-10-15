"""Bind the preserved native control to a short-title cold clone; never launch."""
import argparse
import json
from pathlib import Path

import probe_native_book_oracle as oracle


HERE = Path(__file__).resolve().parent
BASE_HOST_SHA256 = '7fdcb301e1f90e4b0e0b84e35e3521e61b7ba3b953a9a31e6a0cb150df7c5c6c'
MANIFEST_SHA256 = '4cf802c70f38ec55a67a5ccb5a5de928432de0cb436f9b50d49ace2c4cefd691'
SOURCE_DIGEST = 'cef241175e435d0f852f6d55b0b976a880e23b5d0e00dd215e8018dc9e49b3ad'
EXPECTED = {'function': 'set_book_contents', 'title': 'R21 Book A',
            'author': 'R21 Native Loot',
            'pages': ['First authored control.', 'Second authored control.']}

assert oracle.sha(Path(oracle.__file__)) == BASE_HOST_SHA256
oracle.PROJECT = oracle.ROOT / '.runtime/projects/book-r20-native-oracle-short-v2'
oracle.SOURCE_MANIFEST = HERE / 'native-oracle-short-v2/source-manifest.json'
oracle.SOURCE_MANIFEST_SHA256 = MANIFEST_SHA256
oracle.SOURCE_DIGEST = SOURCE_DIGEST
oracle.OWNER = 'book-r20-native-oracle-short-v2'
old_assertion = "assert scalar(tags,'title')=='R21 Native Authored Book A',tags"
assert oracle.ACQUIRE_INSERT.count(old_assertion) == 1
oracle.ACQUIRE_INSERT = oracle.ACQUIRE_INSERT.replace(old_assertion,
    "assert scalar(tags,'title')=='R21 Book A',tags\n"
    "native_pages=scalar(tags,'pages')\n"
    "assert isinstance(native_pages,list) and len(native_pages)==2,tags\n"
    "assert [scalar(root_payload(page) or {},'text') for page in native_pages]=="
    "['First authored control.','Second authored control.'],tags")
base_verify = oracle.verify


def verify():
    assert oracle.sha(Path(oracle.__file__)) == BASE_HOST_SHA256
    loot = json.loads((oracle.PROJECT /
        'behavior_pack/loot_tables/modern_projection/r21_signed_book.json').read_bytes())
    assert loot['pools'][0]['entries'][0]['functions'][0] == EXPECTED
    binding = base_verify()
    binding.update(host_sha256=oracle.sha(Path(__file__)), base_host_sha256=BASE_HOST_SHA256,
                   expected_request=EXPECTED, request_equals_native_data_required=True,
                   previous_attempt_preserved=True)
    return binding


oracle.verify = verify


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('verify')
    command = sub.add_parser('run')
    command.add_argument('--session', type=Path, required=True)
    command.add_argument('--capture-exe', type=Path, required=True)
    command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'verify':
        print(json.dumps(verify()))
    else:
        oracle.run(args)
