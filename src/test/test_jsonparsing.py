import unittest
from son.vmmanager.jsonserver import JsonMsgReader
import logging

logging.basicConfig(level=logging.DEBUG)

class GetJsonSegments(unittest.TestCase):
    def testGetSegments_validSegment(self):
        msgReader = JsonMsgReader()
        jsonString = '{"a": 1, "b": [1,2,3]}'
        segments = msgReader._get_json_segments_(jsonString)
        self.assertEqual(len(segments), 1)
        self.assertIn('start', segments[0])
        self.assertIn('end', segments[0])
        self.assertEqual(segments[0]['start'], 0)
        self.assertEqual(segments[0]['end'], len(jsonString) - 1)

    def testGetSegments_garbageBefore(self):
        msgReader = JsonMsgReader()
        jsonString = 'asdf1wer{"a": 1, "b": [1,2,3]}'
        segments = msgReader._get_json_segments_(jsonString)
        self.assertEqual(len(segments), 1)
        self.assertIn('start', segments[0])
        self.assertIn('end', segments[0])
        self.assertEqual(segments[0]['start'], jsonString.index('{'))
        self.assertEqual(segments[0]['end'], len(jsonString) - 1)

    def testGetSegments_garbageAfter(self):
        msgReader = JsonMsgReader()
        jsonString = '{"a": 1, "b": [1,2,3]}jdnncjd77'
        segments = msgReader._get_json_segments_(jsonString)
        self.assertEqual(len(segments), 1)
        self.assertIn('start', segments[0])
        self.assertIn('end', segments[0])
        self.assertEqual(segments[0]['start'], 0)
        self.assertEqual(segments[0]['end'], jsonString.index('}'))

    def testGetSegments_nested(self):
        msgReader = JsonMsgReader()
        jsonString = '{"a": 1, "b": [1,2,3], "js": {"a": [12,3]}}'
        segments = msgReader._get_json_segments_(jsonString)
        self.assertEqual(len(segments), 1)
        self.assertIn('start', segments[0])
        self.assertIn('end', segments[0])
        self.assertEqual(segments[0]['start'], 0)
        self.assertEqual(segments[0]['end'], len(jsonString) - 1)

    def testGetSegments_incomplete(self):
        msgReader = JsonMsgReader()
        jsonString = '{"a": 1, "b": [1,2'
        segments = msgReader._get_json_segments_(jsonString)
        self.assertEqual(len(segments), 0)


class GetCompleteJsons(unittest.TestCase):
    def testCompleteJson(self):
        jsonMsgReader = JsonMsgReader()
        jsonMsgReader._data = '{"key1": 1, "key2": {"subKey1": [1,2,3]}}'
        jsons = jsonMsgReader._get_complete_jsons_()
        self.assertEqual(len(jsons), 1)
        self.assertEqual(len(jsons[0]), 2)
        self.assertIn("key1", jsons[0])
        self.assertIn("key2", jsons[0])
        self.assertEqual(jsons[0]["key1"], 1)
        self.assertIn("subKey1", jsons[0]["key2"])
        self.assertEqual(jsons[0]["key2"]["subKey1"], [1,2,3])
        self.assertEqual(jsonMsgReader._data, "")

    def testIncompleteJson(self):
        jsonMsgReader = JsonMsgReader()
        jsonMsgReader._data = '{"key1": 1, "key2": {"subKey1": [1,2,3]}}{"key5":'
        jsons = jsonMsgReader._get_complete_jsons_()
        self.assertEqual(len(jsons), 1)
        self.assertEqual(len(jsons[0]), 2)
        self.assertIn("key1", jsons[0])
        self.assertIn("key2", jsons[0])
        self.assertEqual(jsons[0]["key1"], 1)
        self.assertIn("subKey1", jsons[0]["key2"])
        self.assertEqual(jsons[0]["key2"]["subKey1"], [1,2,3])
        self.assertEqual(jsonMsgReader._data, '{"key5":')

    def testInvalidJson(self):
        jsonMsgReader = JsonMsgReader()
        jsonMsgReader._data = '{"key1": 1, "key2": {"subKey1: [1,2,3]}}'
        jsons = jsonMsgReader._get_complete_jsons_()
        self.assertEqual(len(jsons), 0)
        self.assertEqual(jsonMsgReader._data, '')


