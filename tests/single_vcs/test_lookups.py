"""Lookups tests."""
import BeautifulSoup
import json

import pytest


def test_case_assigned(app, case_id, mocked_fogbugz):
    """Test case assigned lookup used for gatekeeper approval form."""
    mocked_fogbugz_instance = mocked_fogbugz.return_value
    mocked_fogbugz_instance.search.return_value = BeautifulSoup.BeautifulSoup("""
    <events>
      <event ixBugEvent="1" ixBug="{case_id}">
      <ixBugEvent>1</ixBugEvent>
        <evt>3</evt>
        <sVerb>Assigned to Captain Caveman</sVerb>
        <ixPerson>3</ixPerson>
        <sPerson>Mikey</sPerson>
        <ixPersonAssignedTo>4</ixPersonAssignedTo>
        <dt>2007-05-06T22:47:59Z</dt>
      </event>
    </events>
    """.format(case_id=case_id))

    mocked_fogbugz_instance.viewPerson.return_value = BeautifulSoup.BeautifulSoup("""
    <people>
      <person>
        <ixPerson>3</ixPerson>
        <sFullName>Old MacDonald</sFullName>
        <sEmail>grandpa@oldmacdonald.com</sEmail>
      </person>
    </people>
    """.format(case_id=case_id))

    response = app.get('/lookup/case_assigned/{case_id}?term=old&page=1'.format(**locals()))
    content = json.loads(response.content)
    assert content == {'results': [{'id': 4, 'text': 'Old MacDonald'}], u'err': u'nil', u'more': False}


def test_case_tags(app, case_id, mocked_fogbugz):
    """Test case tags lookup used for gatekeeper approval form."""
    mocked_fogbugz_instance = mocked_fogbugz.return_value
    mocked_fogbugz_instance.listTags.return_value = BeautifulSoup.BeautifulSoup("""
    <tags>
      <tag><![CDATA[first]]></tag>
      <tag><![CDATA[second]]></tag>
      <tag><![CDATA[third]]></tag>
    </tags>
    """)

    mocked_fogbugz_instance.search.return_value = BeautifulSoup.BeautifulSoup("""
    <tags>
      <tag><![CDATA[case-first]]></tag>
      <tag><![CDATA[case-second]]></tag>
      <tag><![CDATA[case-third]]></tag>
    </tags>
    """)

    response = app.get('/lookup/tags/{case_id}?term=case&page=1'.format(**locals()))
    content = json.loads(response.content)
    assert content == {
        'results': [
            {'id': 'case-first', 'text': 'case-first'},
            {'id': 'case-second', 'text': 'case-second'},
            {'id': 'case-third', 'text': 'case-third'}
        ],
        u'err': u'nil',
        u'more': False}

    response = app.get('/lookup/tags/?term=&page=1'.format(**locals()))
    content = json.loads(response.content)
    assert content == {
        'results': [
            {'id': 'first', 'text': 'first'},
            {'id': 'second', 'text': 'second'},
            {'id': 'third', 'text': 'third'}
        ],
        u'err': u'nil',
        u'more': False}
