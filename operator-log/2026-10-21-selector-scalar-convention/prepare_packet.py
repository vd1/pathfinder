"""Approval-only proposal; read retained evidence without executing it."""
from pathlib import Path
import json,hashlib
from pathfinder import pce,account_exception as ex,account_revision
HERE=Path(__file__).resolve().parent
T=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2/threads/Q010-P030')
ID='ideal-control-definition-20261021';REV='scalar-convention-1'
P=T/'edited/account-amendments'/ID
R=P/'review'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
    pk=HERE/'Q010-P030';source=(P/'candidate.tex').read_text()
    start=source.index('Specifically, let');end=source.index(' Original P endpoint outputs',start)
    before=source[start:end]
    after=r'Specifically, let \(S_0\) and \(S_1\) be the independently selected vacuum and full-field spaces. To distinguish the implementation from the total Hamiltonians \(H(s)\) above, write its scalar-stripped parent matrices as \(K_s=H(s)-c_s\mathbf{1}\), where the retained inactive-plus-nuclear scalar is \(c_s=c_0+s\Delta c\), and set \(W=K_1-K_0\). Only the inactive-plus-nuclear scalar is removed; inactive-core interactions remain in the effective integrals. The implementation takes the lowest eigenvalue \(\varepsilon_0\) and its normalised ground-state vector from \(K_0|_{S_0}\), and \(\varepsilon_1\) from \(K_1|_{S_1}\). It extends the vacuum vector by zero to \(w_0\) in the common 225-determinant parent basis and evaluates \(D_{\mathrm{ind}}=w_0^{T}Ww_0+\Delta c\) and \(I_{\mathrm{ind}}=\varepsilon_1-\varepsilon_0+\Delta c-D_{\mathrm{ind}}\). Thus the static expectation uses the vacuum state in \(S_0\), whereas the full-field energy uses \(S_1\). The scalar increment is restored once in the static component and once in the total endpoint difference from which that static component is subtracted. Equivalently, with total selected-space endpoint energies \(E_s^{\mathrm{sel}}=\varepsilon_s+c_s\) and the earlier total perturbation \(V=W+\Delta c\mathbf{1}\), the same definitions are \(D_{\mathrm{ind}}=w_0^{T}Vw_0\) and \(I_{\mathrm{ind}}=E_1^{\mathrm{sel}}-E_0^{\mathrm{sel}}-D_{\mathrm{ind}}\), without any additional scalar increment. The common-space pooled calculation uses the same scalar restoration with one selected space at both endpoints. Reported component errors subtract the exact-parent static and induction components and use the retained Hartree-to-kcal/mol conversion.'
    assert source.count(before)==1
    candidate=source.replace(before,after,1)
    visibility_before=r'The supplied supplement embeds the selector implementation \texttt{ada/adapt\_qsci/run.py}, but not its numerical inputs \texttt{parent.npz}, \texttt{H-active.npz} and \texttt{V-active.npz}, or the recorded build implementation \texttt{ada/adapt\_qsci/build.py} and its \texttt{build-result.json}.'
    visibility_append=r' The complete retained \texttt{ada/adapt\_qsci/build.py} is now supplied separately as a research-record source, without changing that embedded supplement; this does not supply its numerical inputs, \texttt{build-result.json} or the omitted trajectories and does not make the reported numerical checks independently reproducible.'
    assert candidate.count(visibility_before)==1
    visibility_change=dict(finding='operator-evidence-visibility',before=visibility_before,after=visibility_before+visibility_append)
    candidate=candidate.replace(visibility_before,visibility_change['after'],1)
    (pk/'account-candidate.tex').write_text(candidate)
    critic=R/'reviews/current/critic-computational-chemist.md';text=critic.read_text()
    quote=next(line for line in text.splitlines() if line.startswith('- Required revisions:'))
    projection=dict(version=1,exclude=[],include=[dict(path='ada/adapt_qsci/build.py',sha256=sha(T/'ada/adapt_qsci/build.py'),purpose='Complete retained scalar-stripped matrix construction and separate affine inactive-plus-nuclear scalar storage; read-only, no computation.')])
    delta=dict(parent_candidate_sha256=sha(P/'candidate.tex'),changes=[dict(finding='scalar-convention',before=before,after=after)],findings=[dict(id='scalar-convention',path='reviews/current/critic-computational-chemist.md',sha256=sha(critic),quote=quote)],evidence_projection=projection)
    delta['changes'].append(visibility_change)
    delta['operator_evidence_visibility']=dict(kind='operator-evidence-visibility-v1',authority='Explicit operator instruction to distinguish new separately supplied build.py from the unchanged supplement and preserve numerical omissions; subject to fresh owner approval of this exact contract.',parent_candidate_sha256=sha(P/'candidate.tex'),source='ada/adapt_qsci/build.py',change=visibility_change,append=visibility_append)
    old=json.loads((P/'request.json').read_text())['changes'];assert len(old['changes'])==24
    cumulative={**old,'candidate_sha256':pce._sha(candidate),'changes':old['changes']+delta['changes']}
    write(pk/'revision.json',delta);write(pk/'changes.json',cumulative)
    selected=json.loads((T/'edited/account-amendment.json').read_text());accept=T/'edited/account-amendments'/selected['id']/'acceptance.json'
    c=dict(version=1,pair='Q010-P030',identity=ID,revision=REV,selected_pointer=selected,selected_acceptance_sha256=sha(accept),parent_pointer=json.loads((T/'edited/account-successor.json').read_text()),parent_history_sha256=ex.digest(account_revision._history(P)),parent_candidate_sha256=sha(P/'candidate.tex'),parent_result_sha256=sha(R/'result.json'),parent_frozen_inputs_sha256=sha(R/'frozen-inputs.json'),original_baseline_sha256=old['baseline_sha256'],candidate_sha256=pce._sha(candidate),delta_sha256=ex.digest(delta),cumulative_sha256=ex.digest(cumulative),existing_count=24,total_count=26,finding_ids=['scalar-convention','operator-evidence-visibility'],evidence_projection_sha256=ex.digest(projection))
    write(pk/'revision-exception.json',c)
    sources=[accept,P/'candidate.tex',P/'request.json',P/'successor.json',R/'result.json',R/'frozen-inputs.json',R/'grant.json',critic,T/'ada/adapt_qsci/build.py',T/'ada/adapt_qsci/run.py',T/'ada/adapt_qsci/result.json',T/'status.json',T/'edited/account-amendment.json',T/'edited/account-successor.json']
    write(HERE/'bindings.json',{str(p):sha(p) for p in sources})
    frozen=json.loads((R/'frozen-inputs.json').read_text())
    write(HERE/'visibility-manifest.json',dict(old_external={k:pce._sha(v) for k,v in frozen.items() if k.startswith('sources/external/')},addition=projection['include'][0],omissions=[],old_history_files=account_revision._history(P)))
    reason='Owner-approved exact 24-to-26 same-identity pending-successor revision: clarify the terminal critic scalar-convention finding and separately declared operator evidence-visibility append, preserve all prior records and failed four-role round plus selected23 acceptance. Add complete retained build.py; keep every old source including60count records. One strict pass/fact and five fresh OpenAI roles; no research, reset, editor bypass, source omission or cap change.'
    argv=['--root',str(T.parents[1]),'account-amend-revise','Q010-P030','--id',ID,'--revision',REV,'--packet',str(pk),'--reason',reason,'--approval','<NEW_OWNER_APPROVAL_JSON>']
    write(HERE/'action.json',dict(status='HOLD: explicit new owner approval of exact26 contract required',contract_sha256=ex.digest(c),approval_path=None,prepare_argv_after_owner_approval=argv,apply_argv_after_owner_approval=argv+['--apply'],approval_schema=dict(version=1,decision='approve only after actual new decision',authority='owner',approved_by='actual owner',approval_reference='actual decision reference',contract_sha256=ex.digest(c))))
    print('contract',ex.digest(c),'candidate',pce._sha(candidate))
if __name__=='__main__':main()
