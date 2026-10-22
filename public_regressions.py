# coding: utf-8
"""Public, reviewable regression tests of repaired GitHub educational endpoints.
No network; Flask test_client handles only fictitious seeded app data.
"""
from app import create_app
import pytest
from markupsafe import escape

@pytest.fixture()
def client():
    return create_app({"TESTING":True}).test_client()

@pytest.mark.parametrize("category,expected",[
    ("laptops",b"Security Laptop"),
    ("laptops",b"Packet Analysis Laptop"),
    ("security",b"USB Security Key"),
    ("networking",b"Network Adapter"),
])
def test_sqli_normal_search(client,category,expected):
    response=client.get("/vulnerable/products",query_string={"category":category})
    assert response.status_code==200
    assert expected in response.data

@pytest.mark.parametrize("query",[
    "' OR '1'='1",
    "' OR 1=1 --",
    "laptops' OR 'a'='a",
    "not-a-category",
])
def test_sqli_no_unexpected_products(client,query):
    response=client.get("/vulnerable/products",query_string={"category":query})
    assert response.status_code==200
    assert b"Security Laptop" not in response.data
    assert b"Network Adapter" not in response.data
    assert b"No products found." in response.data

@pytest.mark.parametrize("payload",[
    "<script>alert(42)</script>",
    "<img src=x onerror=alert(42)>",
    "<svg onload=alert(42)>",
    "<b>sample</b>",
])
def test_xss_html_is_escaped(client,payload):
    response=client.get("/vulnerable/xss",query_string={"message":payload})
    assert response.status_code==200
    assert payload.encode() not in response.data
    assert str(escape(payload)).encode() in response.data

@pytest.mark.parametrize("username,own,other,own_marker,other_marker",[
    ("alice",1,2,b"Alice private account information",b"Bob private account information"),
    ("bob",2,1,b"Bob private account information",b"Alice private account information"),
])
def test_idor_owner_and_foreign_access(client,username,own,other,own_marker,other_marker):
    login=client.get("/login/"+username)
    assert login.status_code==302
    mine=client.get(f"/vulnerable/account/{own}")
    assert mine.status_code==200
    assert own_marker in mine.data
    theirs=client.get(f"/vulnerable/account/{other}")
    assert theirs.status_code==403
    assert other_marker not in theirs.data

@pytest.mark.parametrize("account_id",[1,2])
def test_idor_anonymous_blocked(client,account_id):
    response=client.get(f"/vulnerable/account/{account_id}")
    assert response.status_code!=200
    assert b"private account information" not in response.data

