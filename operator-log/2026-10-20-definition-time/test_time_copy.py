from pathlib import Path
import shutil,json
import pytest
from pathfinder import config,account_amend,account_release,pce,pce_recovery,alerts,paper
from test_pce import script
BASE=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2')
PACK=Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-20-definition-time')
@pytest.mark.parametrize('pair',['Q002-P072'])
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
 args=dict(identity='time-swap-definition-20261020',packet=PACK/pair,evidence_root=dt,reason='Copied bounded time-swap definition')
 assert 'no calls' in account_amend.apply(c,pair,**args)
 assert 'accepted;' in account_amend.apply(c,pair,**args,resume=True)
 assert len(calls)==5
 after=pce_recovery.hashes(dt/'edited');assert all(after[k]==v for k,v in before.items() if k!='account-amendment.json')
 assert (dt/'status.json').read_bytes()==science
 account_release.view(c,pair,create=True)
 print(pair,'prior files preserved',len(before),'stub calls',len(calls))
