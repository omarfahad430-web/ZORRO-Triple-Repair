from reverse_linked_list import reverse_linked_list
class Node:
    def __init__(self, value, successor=None):
        self.value=value
        self.successor=successor

def test_empty():
    assert reverse_linked_list(None) is None

def test_singleton():
    n=Node(3)
    assert reverse_linked_list(n) is n

def test_two_nodes():
    tail=Node(2)
    head=Node(1,tail)
    result=reverse_linked_list(head)
    assert result is tail and tail.successor is head and head.successor is None

def test_three_nodes():
    a=Node("a");b=Node("b");c=Node("c")
    a.successor=b;b.successor=c
    result=reverse_linked_list(a)
    assert result is c and c.successor is b and b.successor is a
