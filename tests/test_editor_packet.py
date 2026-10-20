import json
import pytest
from pathfinder import editor_packet as codec


def test_roundtrip_exact_unicode_newlines_and_marker_collisions():
    files = {"z": "same\r\n", "a": "same\r\n", "lf": "same\n", "empty": "", "empty2": "",
             "unicode": "α🙂e\u0301", "markers": codec.MAGIC + '{"files":[]}\ntrailing\n',
             "json": '{"escaped":"\\\\n","literal":"\\n"}'}
    payload, header = codec.encode(files)
    assert codec.decode(payload) == files
    assert codec.encode(dict(reversed(list(files.items())))) == (payload, header)
    assert header["aliases"] == {"empty2": "empty", "z": "a"}
    assert {n: v.encode() for n, v in codec.decode(payload).items()} == {n: v.encode() for n, v in files.items()}


@pytest.mark.parametrize("mutation", ["truncate", "append", "hash", "length", "alias", "duplicate"])
def test_corruption_rejected(mutation):
    payload, header = codec.encode({"a": "α\n", "b": "α\n", "c": "different"})
    _, _, body = payload[len(codec.MAGIC):].partition("\n")
    if mutation == "truncate": payload = payload[:-1]
    elif mutation == "append": payload += "hidden"
    else:
        if mutation == "hash": header["files"][0]["sha256"] = "0" * 64
        if mutation == "length": header["files"][0]["chars"] = True
        if mutation == "alias": header["aliases"]["b"] = "missing"
        if mutation == "duplicate": header["files"][1]["path"] = "a"
        payload = codec.MAGIC + json.dumps(header) + "\n" + body
    with pytest.raises(ValueError): codec.decode(payload)
