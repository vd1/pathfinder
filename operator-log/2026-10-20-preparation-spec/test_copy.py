from pathlib import Path
import shutil,json
import pytest
from pathfinder import config,account_amend,account_release,pce,pce_recovery,alerts,paper
from test_pce import script
BASE=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2')
PACK=Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-20-preparation-spec')
MARKERS=['3A@3D~3A:final', 'product_baseline.md', 'Joint scenario signs and marginal magnitudes']
@pytest.mark.parametrize('pair',['Q053-P011'])
def test_actual_copy(tmp_path,monkeypatch,pair):
 monkeypatch.setenv('PATHFINDER_ACCOUNTS',str(tmp_path/'accounts'));monkeypatch.setenv('PATHFINDER_SOURCE_CACHE',str(tmp_path/'pool'));monkeypatch.setenv('PATHFINDER_OFFLINE','1')
 monkeypatch.setattr(alerts,'_desktop',lambda *a:'suppressed');monkeypatch.setattr(paper,'_arxiv_titles',lambda ids:{})
 src=BASE;dst=tmp_path/'copy';dst.mkdir()
 for name in ['campaign.json','import.json','Q.jsonl','P.jsonl','shortlist.json']:
  if (src/name).exists():shutil.copy(src/name,dst/name)
 st=src/'threads'/pair;dt=dst/'threads'/pair;dt.mkdir(parents=True)
 for p in st.iterdir():
  if p.is_file() and p.suffix in ('.json','.jsonl','.tex'):shutil.copy(p,dt/p.name)
 for name in ('edited','inputs'):shutil.copytree(st/name,dt/name)
 for ledger in st.glob('branches/*/ledger.jsonl'):
  p=dt/ledger.relative_to(st);p.parent.mkdir(parents=True,exist_ok=True);shutil.copy(ledger,p)
 for row in json.loads((PACK/pair/'evidence.json').read_text())['source_files']:
  name=row['path'];p=dt/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy(st/name,p)
 c=config.load(dst);c.backend='stub';c.raw['routes']={};c.raw['refusal_fallback']=None
 before=pce_recovery.hashes(dt/'edited');science=(dt/'status.json').read_bytes();calls=script(monkeypatch,c)
 args=dict(identity='preparation-spec-20261020',packet=PACK/pair,evidence_root=dt,reason='Copied bounded retained-definition clarification')
 assert 'no calls' in account_amend.apply(c,pair,**args)
 frozen=json.loads((dt/'edited/account-amendments/preparation-spec-20261020/review/frozen-inputs.json').read_text())
 assert '3A@3D~3A:final' in '\n'.join(frozen.values())
 assert 'product_baseline.md' in '\n'.join(frozen.values())
 assert 'nb' in '\n'.join(frozen.values())
 assert 'Joint scenario signs and marginal magnitudes' in '\n'.join(frozen.values())
 assert 'accepted;' in account_amend.apply(c,pair,**args,resume=True)
 assert len(calls)==5
 review=dt/'edited/account-amendments'/args['identity']/'review'
 visibility=list((review/'visibility').glob('*.json'))
 assert len(visibility)==5
 assert all(not json.loads(p.read_text())['truncated'] for p in visibility)
 for call in calls:
  if call['role'] in ('fact-checker','critic'):
   for marker in MARKERS: assert marker in call['prompt']
 after=pce_recovery.hashes(dt/'edited');assert all(after[k]==v for k,v in before.items() if k!='account-amendment.json')
 assert (dt/'status.json').read_bytes()==science
 account_release.view(c,pair,create=True)
 print(pair,'prior files preserved',len(before),'stub calls',len(calls))
