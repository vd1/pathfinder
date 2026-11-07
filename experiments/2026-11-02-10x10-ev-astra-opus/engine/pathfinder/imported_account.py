"""Read-only validation of accepted EVA2 imports for account publication."""
import json
import re
from . import pce
from .import_eva2 import _sha


def source(campaign, pair_id, edit_record):
    ed = campaign.thread_dir(pair_id) / 'edited'
    root = ed / 'eva2-pce'
    try:
        imported = json.loads(campaign.path('import.json').read_text())['edit']
        delivery = json.loads((root / 'delivery.json').read_text())
        render = json.loads((root / 'account.render.json').read_text())
        body = (ed / 'note.tex').read_bytes()
        original = (root / 'account.tex').read_bytes()
        wrapper = (root / 'account.build.tex').read_bytes()
        if (edit_record.get('status') != 'done' or edit_record.get('editorial_status') != 'accepted'
                or edit_record.get('imported_from') != 'eva2 PCE'
                or imported.get('editorial_status') != 'accepted' or imported.get('pce_result') != 'accepted'
                or imported.get('kept_as') != 'edited/eva2-pce'
                or edit_record.get('source') != imported.get('source')
                or delivery.get('editorial_status') != 'accepted'
                or (delivery.get('pce_result') or {}).get('status') != 'accepted'
                or not render.get('passed')):
            raise pce.Changed('EVA2 import does not retain accepted editorial delivery and render records')
        if (body != original or _sha(ed / 'note.tex') != imported.get('note_sha256')
                or _sha(ed / 'note.tex') != render.get('source_sha256')
                or _sha(root / 'account.build.tex') != render.get('document_sha256')
                or _sha(ed / 'note.pdf') != imported.get('pdf_sha256')
                or _sha(root / 'account.pdf') != render.get('pdf_sha256')
                or imported.get('pdf_sha256') != render.get('pdf_sha256')
                or body not in wrapper):
            raise pce.Changed('EVA2 imported body, wrapper or PDF differs from its recorded acceptance/render evidence')
        text = wrapper.decode('utf-8')
        if not text.lstrip().startswith('\\documentclass') or '\\end{document}' not in text:
            raise pce.Changed('EVA2 retained wrapper is not a whole LaTeX document')
        bib_path = root / 'references.bib'
        if not bib_path.exists() and re.search(r'\\(?:bibliography|addbibresource|(?:no)?cite\w*)\b', text):
            raise pce.Changed('EVA2 account needs a bibliography that was not retained')
        bib = bib_path.read_text() if bib_path.exists() else ''
        files = [campaign.path('import.json'), ed / 'edit.json', ed / 'note.tex', ed / 'note.pdf',
                 root / 'delivery.json', root / 'account.render.json', root / 'account.tex',
                 root / 'account.build.tex', root / 'account.pdf']
        if bib_path.exists():
            files.append(bib_path)
        provenance = {'kind': 'imported EVA2 PCE editorial acceptance', 'workflow': 'edited/eva2-pce',
                      'body_sha256': _sha(ed / 'note.tex'), 'wrapper_sha256': _sha(root / 'account.build.tex'),
                      'evidence_sha256': {str(p.relative_to(campaign.root)): _sha(p) for p in files},
                      'bibliography': 'retained' if bib_path.exists() else 'none; original uses prose references'}
        return text, bib, provenance
    except (OSError, ValueError, KeyError) as error:
        if isinstance(error, pce.Changed):
            raise
        raise pce.Changed(f'incomplete EVA2 account acceptance evidence: {error}') from error
