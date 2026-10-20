import json
from types import SimpleNamespace
import pytest
from pathfinder import account_present, presentation, pce

@pytest.mark.parametrize('after,allowed,blocked',[
 ('The rings include Phe60.',('Phe60',),False),
 ('The rings include Phe60.',(),True),
 ('The rings include Phe61.',('Phe60',),True),
 ('The rings include Phe60 with energy 60.',('Phe60',),True),
 ('The rings include Phe60 and 0.4 nm.',('Phe60',),True),
 ('The rings include Phe600.',('Phe60',),True),
 (r'The rings include Phe60. \[x=60\]',('Phe60',),True),
])
def test_numeric_guard_only_exempts_exact_bound_label(after,allowed,blocked):
 assert bool(presentation.guard('The ring is present.','The ring is present. '+after,'The ring is present.','',residue_identifiers=allowed))==blocked

def test_existing_residue_cannot_be_replaced():
 assert presentation.guard('Phe113 is present.','Phe60 is present.','','',residue_identifiers=('Phe60',))

@pytest.mark.parametrize('damage',[None,'hash','missing','numeric','duplicate'])
def test_retained_label_binding(tmp_path,damage):
 (tmp_path/'inputs').mkdir();source=tmp_path/'inputs/Q.txt';source.write_text('The phenyl rings of Phe113 and Phe60 are listed.')
 entry=dict(source='inputs/Q.txt',sha256=pce._sha(source.read_text()),quote=source.read_text(),where='The ring wall.')
 item=dict(identifier='Phe60',source='inputs/Q.txt')
 if damage=='hash':entry['sha256']='wrong'
 if damage=='missing':item['identifier']='Phe61'
 if damage=='numeric':item['identifier']='60'
 context=dict(version=1,contexts=[entry],residue_identifiers=[item]*(2 if damage=='duplicate' else 1))
 path=tmp_path/'context.json';path.write_text(json.dumps(context));c=SimpleNamespace(thread_dir=lambda pair:tmp_path,peers=('ada','emmy'))
 if damage:
  with pytest.raises(pce.Changed):account_present._context(c,'pair',tmp_path,path)
 else:assert account_present._context(c,'pair',tmp_path,path)[0]==context
