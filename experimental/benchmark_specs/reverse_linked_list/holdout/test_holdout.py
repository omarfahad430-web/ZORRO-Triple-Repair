from reverse_linked_list import reverse_linked_list
class Node:
    def __init__(self,value,successor=None):
        self.value=value
        self.successor=successor

def test_four_nodes():
    nodes=[Node(i) for i in range(4)]
    for a,b in zip(nodes,nodes[1:]):
        a.successor=b
    head=reverse_linked_list(nodes[0])
    values=[]
    while head:
        values.append(head.value)
        assert len(values) <= 4
        head=head.successor
    assert values == [3,2,1,0]
