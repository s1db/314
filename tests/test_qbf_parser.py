import pytest
from src.instance_parsers.qbf import QBFParser


def test_simple_qbf():
    content = """c Example QBF
p cnf 4 2
e 1 2 0
a 3 4 0
-1 2 0
3 -4 0"""
    instance = QBFParser.from_qdimacs(content)
    assert instance.num_vars == 4
    assert instance.num_clauses == 2
    assert len(instance.quantifiers) == 2
    assert instance.quantifiers[0] == ("e", [1, 2])
    assert instance.quantifiers[1] == ("a", [3, 4])
    assert instance.clauses == [[-1, 2], [3, -4]]


def test_empty_clause():
    content = """p cnf 2 1
a 1 2 0
0"""
    instance = QBFParser.from_qdimacs(content)
    assert instance.clauses == [[]]


def test_multiline_quantifiers():
    content = """p cnf 4 1
e 1 
2 0
a 3 4 0
1 2 3 4 0"""
    instance = QBFParser.from_qdimacs(content)
    assert instance.quantifiers[0] == ("e", [1, 2])


def test_comments_everywhere():
    content = """c start
p cnf 2 1
c middle
e 1 2 0
c nearly there
1 2 0
c end"""
    instance = QBFParser.from_qdimacs(content)
    assert instance.num_vars == 2
    assert len(instance.clauses) == 1


def test_invalid_header():
    content = """c invalid
p sat 1 1
1 0"""
    with pytest.raises(ValueError):
        QBFParser.from_qdimacs(content)


def test_missing_header():
    content = """e 1 0
1 0"""
    with pytest.raises(ValueError):
        QBFParser.from_qdimacs(content)
