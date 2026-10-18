"""The correction guard of the presentation pass (nobel pilot, 18 October 2026): a correction may add definitions
and reword, but in the pilot a correction editor told so still introduced one meaning error per paper (a claim
about cited work, a constant reattributed to a cited theorem, Theorem 2 placed inside the Section 4 construction).
The guard compares the corrected manuscript with the one before it, sentence by sentence: a sentence of the
accepted paper may gain words but not lose or change them, unless the correction restores the accepted wording;
inserted text may not cite, name an author of the bibliography, bring a number the paper did not have, refer to
a numbered theorem or section, or display a formula."""
from pathfinder.presentation import guard

BIB = "@article{ls20,\n  author = {Luongo, Alessandro and Shao, Changpeng},\n  title = {Quantum algorithms},\n  year = {2020}\n}\n"
HEAD = "\\documentclass{article}\n\\begin{document}\n"
ACCEPTED = HEAD + ("Let \\(U\\) be a unitary. The cost is \\(O(r^{-2})\\) for the whole measure.\n\n"
                   "We bound the error by two terms. This settles the question.\n\\end{document}\n")


def _with(body):
    return HEAD + body + "\n\\end{document}\n"


PASS = _with("Let \\(U\\) be a unitary. The cost is \\(O(r^{-2})\\) for the whole measure.\n\n"
             "We bound the error by two terms. This settles the question for all measures.")


def test_a_definition_added_as_a_new_sentence_passes():
    after = PASS.replace("Let \\(U\\) be a unitary.", "Let \\(U\\) be a unitary. Here \\(\\lambda_l\\) denotes the l-th weight.")
    assert guard(PASS, after, ACCEPTED, BIB) == []


def test_words_added_inside_an_accepted_sentence_pass():
    after = PASS.replace("for the whole measure.", "for the whole measure, where \\(r\\) is the target accuracy.")
    assert guard(PASS, after, ACCEPTED, BIB) == []


def test_changing_the_wording_of_an_accepted_sentence_is_refused():
    after = PASS.replace("We bound the error by two terms.", "We bound the error by a single term.")
    assert any("changes accepted wording" in v for v in guard(PASS, after, ACCEPTED, BIB))


def test_deleting_an_accepted_sentence_is_refused():
    after = PASS.replace("We bound the error by two terms. ", "")
    assert any("deletes accepted text" in v for v in guard(PASS, after, ACCEPTED, BIB))


def test_restoring_the_accepted_wording_of_a_sentence_the_pass_changed_passes():
    after = PASS.replace("This settles the question for all measures.", "This settles the question.")
    assert guard(PASS, after, ACCEPTED, BIB) == []


def test_inserted_text_may_not_cite_or_name_an_author():
    cites = PASS.replace("a unitary.", "a unitary. This constant is fixed by \\cite{ls20}.")
    names = PASS.replace("a unitary.", "a unitary. Luongo shows the same bound.")
    assert any("cites" in v for v in guard(PASS, cites, ACCEPTED, BIB))
    assert any("names an author" in v for v in guard(PASS, names, ACCEPTED, BIB))


def test_inserted_text_may_not_bring_a_new_number_a_cross_reference_or_a_display():
    number = PASS.replace("a unitary.", "a unitary. The deflation constant is 7.")
    ref = PASS.replace("a unitary.", "a unitary. This is the construction of Theorem 2.")
    display = PASS.replace("a unitary.", "a unitary. We set \\[ c = r^{-1}. \\]")
    assert any("number 7" in v for v in guard(PASS, number, ACCEPTED, BIB))
    assert any("cross-reference" in v for v in guard(PASS, ref, ACCEPTED, BIB))
    assert any("displayed formula" in v for v in guard(PASS, display, ACCEPTED, BIB))


def test_comments_and_the_preamble_are_not_compared():
    after = PASS.replace("\\begin{document}", "\\usepackage{x}\n\\begin{document}").replace(
        "for the whole measure.\n", "for the whole measure. % ledger 12\n")
    assert guard(PASS, after, ACCEPTED, BIB) == []
