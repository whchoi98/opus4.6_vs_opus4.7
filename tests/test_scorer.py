from scorers.judge import _parse_verdict


def test_parse_verdict_a_better():
    txt = "VERDICT: A_better\nRATIONALE: Response A was more specific."
    v, r = _parse_verdict(txt)
    assert v == "4.7_better"
    assert "specific" in r


def test_parse_verdict_b_better():
    txt = "VERDICT: B_better\nRATIONALE: Response B used the tools."
    v, r = _parse_verdict(txt)
    assert v == "4.6_better"
    assert "tools" in r


def test_parse_verdict_tie():
    txt = "VERDICT: tie\nRATIONALE: Equal quality."
    v, r = _parse_verdict(txt)
    assert v == "tie"
