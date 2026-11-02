#!/usr/bin/env python3
"""Independent fail-closed contract tests for the engine-first vertical slice."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import fresh_wcl_engine_v1 as eng


class TestFreshEngineV1(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.code="SYNTH123456"
        self.fight=9
        self.calls=[]
        self.revision=1

    def mock_query(self,query,variables):
        if "FreshReport" in query:
            return {"reportData":{"report":{"code":self.code,"revision":self.revision,
                  "fights":[{"id":9,"startTime":0,"endTime":100,"encounterID":500,"difficulty":4,"inProgress":False}]}}}
        self.calls.append(variables["start"])
        return {"reportData":{"report":{"events":{"data":[
            {"timestamp":0,"type":"applybuff","abilityGameID":301,"targetID":7,"stack":1},
            {"timestamp":1,"type":"cast","abilityGameID":701,"sourceID":7}],
            "nextPageTimestamp":None}}}}

    def directory(self):
        return self.root/self.code/"fight_9"

    def assert_error(self,func,token):
        with self.assertRaises(eng.EngineError) as cm:func()
        self.assertIn(token,str(cm.exception))

    def test_default_self_test_never_opens_network(self):
        with patch.object(eng.request,"urlopen",side_effect=AssertionError("network attempted")):
            self.assertGreaterEqual(eng.self_test()["check_count"],21)

    def test_empty_cache_collect_and_replay(self):
        out=eng.collect(self.mock_query,self.code,9,self.root)
        self.assertEqual((out["status"],out["pages"]),("COMPLETE",1))
        data=eng.replay(self.directory())
        self.assertEqual(data["decision_count"],1)
        self.assertEqual(data["decisions"][0]["aura_pre"]["301"],{"active":True,"stacks":1})
        self.assertEqual(self.calls,[0])

    def test_revision_changes_fail_before_any_event_query(self):
        eng.collect(self.mock_query,self.code,9,self.root)
        self.revision=2
        self.assert_error(lambda:eng.collect(self.mock_query,self.code,9,self.root),"REVISION_CHANGED")
        self.assertEqual(self.calls,[0])

    def test_page_mutation_is_not_silent(self):
        eng.collect(self.mock_query,self.code,9,self.root)
        (self.directory()/"page_00000.json").write_text("{}")
        self.assert_error(lambda:eng.replay(self.directory()),"PAGE_TAMPERED")
        self.assert_error(lambda:eng.collect(self.mock_query,self.code,9,self.root),"PAGE_TAMPERED")

    def test_invalid_wcl_response_fails_before_checkpoint(self):
        def wrong(q,v):
            if "FreshReport" in q:return self.mock_query(q,v)
            return {"reportData":{"report":{"events":{"data":["unexpected"],"nextPageTimestamp":None}}}}
        self.assert_error(lambda:eng.collect(wrong,self.code,9,self.root),"EVENT_IDENTITY")
        self.assertFalse((self.directory()/"checkpoint.json").exists())

    def test_untracked_directory_is_rejected(self):
        self.directory().mkdir(parents=True)
        (self.directory()/"page_00000.json").write_text("untracked")
        self.assert_error(lambda:eng.collect(self.mock_query,self.code,9,self.root),"UNTRACKED_DIRECTORY")

    def test_orphan_invalid_json_rejected(self):
        eng.collect(self.mock_query,self.code,9,self.root,max_pages=1)
        # Already completed; an unexpected page cannot be accepted.
        (self.directory()/"page_00001.json").write_text("INVALID")
        self.assert_error(lambda:eng.collect(self.mock_query,self.code,9,self.root),"UNCOMMITTED_OR_MISSING_PAGE")

    def test_unknown_stacks_never_invented(self):
        self.assertEqual(eng._aura_transition({"type":"removebuffstack"}),{"active":None,"stacks":None})
        self.assertEqual(eng._aura_transition({"type":"removebuffstack","stack":0,"stacks":8}),{"active":False,"stacks":0})
        self.assertIsNone(eng._ability({"ability":{"name":"Localized"}}))

    def test_no_path_traversal_through_report_code(self):
        self.assert_error(lambda:eng.collect(self.mock_query,"../../secret",9,self.root),"REPORT_OR_FIGHT_ID_INVALID")

    def test_oauth_and_graphql_urls_pinned_official_public(self):
        self.assertEqual(eng.TOKEN_URL,"https://www.warcraftlogs.com/oauth/token")
        self.assertEqual(eng.GRAPHQL_URL,"https://www.warcraftlogs.com/api/v2/client")
        self.assertIn("nextPageTimestamp",eng.EVENTS_QUERY)
        self.assertIn("includeResources:true",eng.EVENTS_QUERY)


if __name__=="__main__":unittest.main()
