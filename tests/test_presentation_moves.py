from pathfinder.presentation import guard


def doc(*sentences):
    return '\\begin{document}\n'+'\n\n'.join(sentences)+'\n\\end{document}'


def test_exact_move_and_rewrap():
    sentence='A tilde suppresses logarithmic\nfactors in the parameters.'
    before=doc('Introduction.', 'Later material.',sentence)
    after=doc('Introduction.',sentence.replace('\n',' '),'Later material.')
    assert guard(before,after,before,'')==[]


def test_move_does_not_hide_real_deletion_or_change():
    before=doc('A bound costs 4 steps.', 'The scope is restricted.', 'Conclusion.')
    moved=doc('Conclusion.','A bound costs 4 steps.')
    assert any('deletes accepted' in h for h in guard(before,moved,before,''))
    changed=doc('Conclusion.','A bound costs 5 steps.', 'The scope is restricted.')
    assert guard(before,changed,before,'')


def test_duplicate_sentence_cannot_hide_deletion():
    before=doc('The scope is restricted.','An intervening sentence.','The scope is restricted.')
    after=doc('An intervening sentence.','The scope is restricted.')
    assert any('deletes accepted' in h for h in guard(before,after,before,''))


def test_moved_citation_is_not_new_but_new_citation_is():
    before=doc('Introduction.', r'A bound follows \cite{Smith}.', 'Conclusion.')
    after=doc(r'A bound follows \cite{Smith}.','Introduction.','Conclusion.')
    assert not guard(before,after,before,'')
    assert guard(before,after.replace('Conclusion.',r'Conclusion \cite{New}.'),before,'')
