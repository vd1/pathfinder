import json
import pytest
from pathfinder import account_amend, account_review, pce
from test_account_amend import packet

@pytest.mark.parametrize('damage',[None,'line-endings','content'])
def test_custody_preserves_exact_utf8_evidence_bytes(tmp_path,damage):
 c,ed,candidate,args=packet(tmp_path)
 path=c.thread_dir('Q1P1')/'branches/branch-1/derivation.txt'
 raw=b'An empty minimum is infinity.\r\nRetained evidence.\r\n'
 path.write_bytes(raw)
 ep=args['packet']/'evidence.json';data=json.loads(ep.read_text());data['source_files'][0]['sha256']=pce._sha(raw.decode('utf-8'));ep.write_text(json.dumps(data))
 assert 'no calls' in account_amend.apply(c,'Q1P1',**args)
 root=account_amend._root(c,'Q1P1',args['identity'])
 assert account_review.custody(c,'Q1P1',root)[1]==candidate
 assert path.read_bytes()==raw
 if damage:
  path.write_bytes(raw.replace(b'\r\n',b'\n') if damage=='line-endings' else raw.replace(b'infinity',b'finite'))
  with pytest.raises(pce.Changed,match='evidence changed'):account_review.custody(c,'Q1P1',root)
