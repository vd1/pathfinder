"""Create an approval-only exact proposal from retained sources; no live writes."""
from pathlib import Path
import hashlib,json
from pathfinder import account_exception as ex,pce
HERE=Path(__file__).resolve().parent
THREAD=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2/threads/Q010-P030')
PARENT=THREAD/'edited/account-amendments/pool-component-definition-20261020'
PUB=THREAD/'edited/publication/036eeec4880046209d3b96f4b754a403952fba46c9ff06300c0c7c59cb3b3769'
IDENTITY='ideal-control-definition-20261021'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
    pack=HERE/'Q010-P030'
    source=(PARENT/'candidate.tex').read_text()
    before='An idealised control selected determinants using exact parent probabilities, without shots or an ADAPT circuit.'
    after=before+r' Here field-only means selection of the top \(R\) determinants by exact parent ground-state probability at full MM-charge scaling, \(s=1\). For the ideal pooled space, the candidates are the union of the top-\(R\) lists at vacuum, half field and full field, \(s=0,1/2,1\); the \(R\) largest equal-weight sums of the three exact probabilities are retained, with increasing determinant index breaking ties. The field scales the inherited MM charges in the same fixed vacuum-orbital parent CAS. This deterministic probability rule is distinct from the finite-shot frequency-pooling construction below.'
    assert source.count(before)==1
    candidate=source.replace(before,after,1)
    (pack/'account-candidate.tex').write_text(candidate)
    script=THREAD/'ada/water_selector.py'
    projection=dict(version=1,exclude=[],include=[dict(path='ada/water_selector.py',sha256=sha(script),purpose='Complete retained ideal-control implementation: field scaling, exact probabilities, top-R union/ranking/ties and common fixed-orbital model. No execution or new results.')])
    delta=dict(parent_candidate_sha256=sha(PARENT/'candidate.tex'),parent_acceptance_sha256=sha(PARENT/'acceptance.json'),returned_findings_sha256=sha(PUB/'presentation/amend-findings.json'),changes=[dict(finding='P1',before=before,after=after)],evidence_projection=projection)
    write(pack/'successor.json',delta)
    req=json.loads((PARENT/'request.json').read_text());old=req['changes'];assert len(old['changes'])==23
    cumulative={**old,'candidate_sha256':pce._sha(candidate),'changes':old['changes']+delta['changes']}
    contract=dict(version=2,pair='Q010-P030',identity=IDENTITY,parent_pointer=json.loads((THREAD/'edited/account-amendment.json').read_text()),parent_request_sha256=sha(PARENT/'request.json'),parent_frozen_inputs_sha256=sha(PARENT/'review/frozen-inputs.json'),parent_candidate_sha256=delta['parent_candidate_sha256'],parent_acceptance_sha256=delta['parent_acceptance_sha256'],returned_findings_sha256=delta['returned_findings_sha256'],candidate_sha256=pce._sha(candidate),delta_sha256=ex.digest(delta),original_baseline_sha256=old['baseline_sha256'],cumulative_sha256=ex.digest(cumulative),existing_count=23,total_count=24,finding_ids=['P1'],evidence_projection_sha256=ex.digest(projection))
    write(pack/'history-exception.json',contract);write(HERE/'cumulative-changes.json',cumulative)
    files=json.loads((PARENT/'review/frozen-inputs.json').read_text())
    write(HERE/'visibility-manifest.json',dict(old_external={k:pce._sha(v) for k,v in files.items() if k.startswith('sources/external/')},additional_complete_file=projection['include'][0],omissions=[],selected_60_counts_preserved=True))
    names=[PARENT/'acceptance.json',PARENT/'request.json',PARENT/'candidate.tex',PARENT/'review/frozen-inputs.json',PARENT/'review/result.json',PUB/'presentation/state.json',PUB/'presentation/amend-findings.json',PUB/'presentation/correct-1/check.json',script,THREAD/'ada/water_selector_interpretation.txt',THREAD/'ada/adapt_qsci/result.json',THREAD/'edited/account-amendment.json',THREAD/'status.json']
    write(HERE/'bindings.json',{str(p):sha(p) for p in names if p.exists()})
    reason='Owner-approved exact 23-to-24 accepted-successor exception for returned P1 ideal-control definition only; preserve every prior record and all inherited scientific inputs including selected sixty count records. Add complete retained water_selector.py with research-record standing. One strict fixed-candidate pass and one fact check, five OpenAI roles, no research, withdrawal, threshold change, reset or cap increase; selection changes only after genuine acceptance and build.'
    argv=['--root',str(THREAD.parents[1]),'account-amend-successor','Q010-P030','--id',IDENTITY,'--packet',str(pack),'--reason',reason,'--approval','<OWNER_APPROVAL_JSON>']
    write(HERE/'action.json',dict(status='HOLD: explicit owner approval of exact 24-record contract required',contract_sha256=ex.digest(contract),prepare_argv_after_owner_approval=argv,apply_argv_after_owner_approval=argv+['--apply'],approval_path=None,approval_schema=dict(version=1,decision='approve only after actual owner decision',authority='owner',approved_by='actual approving owner',approval_reference='actual decision reference',contract_sha256=ex.digest(contract))))
    print(ex.digest(contract),pce._sha(candidate))
if __name__=='__main__':main()
