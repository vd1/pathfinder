import json
import pytest
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('prototype',Path(__file__).with_name('prototype_editor_packet.py'))
ep=importlib.util.module_from_spec(spec);spec.loader.exec_module(ep)


def fixture():
    start='α line\r\n'*200;end='end 😀\n'*200
    return {'a.tex':start+'INSERT'+end,'b.tex':start+end,'c.tex':start+end,
            'd.json':'{"marker":"PATHFINDER-EDITOR-SPANS-V1\\n"}\n','empty':''}


def test_lossless_unicode_aliases_and_exact_spans():
    files=fixture();payload,header=ep.encode_spans(files)
    assert ep.decode_spans(payload)==files
    row=next(r for r in header['files'] if r['path']=='b.tex')
    assert all('copy' in s for s in row['segments'])
    assert header['aliases']=={'c.tex':'b.tex'}
    assert ep.encode_spans(files)[0]==payload


@pytest.mark.parametrize('bad',['forward','negative','overrun','boolean','file-hash','literal-hash','literal-length','duplicate','trailing','alias','segment','file-count'])
def test_rejects_nonlossless_spans(bad):
    payload,header=ep.encode_spans(fixture());body=payload[len(ep.SPAN_MAGIC):].partition('\n')[2]
    a,b=header['files'][:2]
    if bad=='forward':b['segments'][0]['copy']='missing'
    if bad=='negative':b['segments'][0]['start']=-1
    if bad=='overrun':b['segments'][0]['end']=10**9
    if bad=='boolean':b['segments'][0]['start']=False
    if bad=='file-hash':b['sha256']='0'*64
    if bad=='literal-hash':a['segments'][0]['sha256']='0'*64
    if bad=='literal-length':a['segments'][0]['chars']+=1
    if bad=='duplicate':b['path']=a['path']
    if bad=='trailing':body+='x'
    if bad=='alias':header['aliases']['c.tex']='absent'
    if bad=='segment':b['segments'][0]['extra']=True
    if bad=='file-count':b['chars']+=1
    broken=ep.SPAN_MAGIC+json.dumps(header)+'\n'+body
    with pytest.raises(ValueError):ep.decode_spans(broken)


def test_manuscript_multiblock_unicode_crlf_and_literals():
    blocks = [((f"section{i} α😀 e\u0301\r\n") * 40) for i in range(4)]
    current = "NEW\r\n" + "new interlude\r\n".join(blocks) + "\nEND"
    original = "OLD\n" + "old interlude\n".join(blocks) + "\r\nEND"
    files = {"drafts/current.tex": current, "sources/internal/original.tex": original}
    payload, header = ep.encode_spans(files)
    assert ep.decode_spans(payload) == files
    row = next(r for r in header["files"] if r["path"] == "sources/internal/original.tex")
    assert sum("copy" in s for s in row["segments"]) == 4
    assert all(s["copy"] == "drafts/current.tex" for s in row["segments"] if "copy" in s)
    assert ep.encode_spans(dict(reversed(list(files.items()))))[0] == payload
    # External material never receives interior-block matching.
    _, external_header = ep.encode_spans({"drafts/current.tex": current, "sources/external/note.tex": original})
    external = next(r for r in external_header["files"] if r["path"] == "sources/external/note.tex")
    assert sum("copy" in s for s in external["segments"]) <= 2


def test_multiblock_bounds_and_no_normalisation():
    assert ep._manuscript_blocks("drafts/current.tex", "x"*200001, "x"*200001) is None
    assert ep._manuscript_blocks("drafts/current.tex", "a\n"*2049, "a\n"*2049) is None
    assert ep._manuscript_blocks("drafts/current.tex", "é\r\n"*100, "e\u0301\n"*100) is None
    blocks = [f"block {i} " + "x"*300 + "\n" for i in range(65)]
    a = "old\n".join(blocks)
    b = "new\n".join(blocks)
    assert ep._manuscript_blocks("drafts/current.tex", a, b) is None


@pytest.mark.parametrize("source", ["drafts/current.tex", "future.tex", "alias.tex"])
def test_no_self_forward_or_alias_span(source):
    text = "abc😀\r\n"*100
    header = {"files": [{"path": "drafts/current.tex", "chars": len(text),
                        "sha256": ep.digest(text),
                        "segments": [{"copy": source, "start": 0, "end": len(text)}]}],
              "aliases": {"alias.tex": "drafts/current.tex"}}
    with pytest.raises(ValueError, match="backward"):
        ep.decode_spans(ep.SPAN_MAGIC + json.dumps(header) + "\n")


def test_overlap_is_exact_concatenation_not_union():
    base = "α😀\r\nabcdef"
    text = base[:6] + base[3:8]
    header = {"files": [
        {"path": "a", "chars": len(base), "sha256": ep.digest(base),
         "segments": [{"chars": len(base), "sha256": ep.digest(base)}]},
        {"path": "b", "chars": len(text), "sha256": ep.digest(text),
         "segments": [{"copy": "a", "start": 0, "end": 6},
                      {"copy": "a", "start": 3, "end": 8}]}], "aliases": {}}
    payload = ep.SPAN_MAGIC + json.dumps(header) + "\n" + base + "\n"
    assert ep.decode_spans(payload) == {"a": base, "b": text}
    header["files"][1]["sha256"] = ep.digest(base[:8])
    with pytest.raises(ValueError, match="hash"):
        ep.decode_spans(ep.SPAN_MAGIC + json.dumps(header) + "\n" + base + "\n")
