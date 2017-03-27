from son.vmmanager.jsonserver import IJsonProcessor as P

import unittest
import logging
import json

logging.basicConfig(level=logging.DEBUG)

class ProcessorResult(unittest.TestCase):

    def testInvalidStatus(self):
        self.assertRaises(Exception, P.Result, None, "")

    def testInvalidMessage(self):
        self.assertRaises(Exception, P.Result,
                          P.Result.OK, None)

    def testInvalidArgs(self):
        self.assertRaises(Exception, P.Result,
                          P.Result.OK, "Fine",
                          "Something not dict")

    def testBidirectionalConversion(self):
        r = P.Result(P.Result.OK, "Fine")
        js = r.json()
        rr = P.Result.parse(js)

        self.assertEqual(r.status, rr.status)
        self.assertEqual(r.message, rr.message)

    def testValidParsing(self):
        result = P.Result.parse('{"status": %d, "message": "Fine"}' % P.Result.OK)

        self.assertEqual(result.status, P.Result.OK)
        self.assertEqual(result.message, "Fine")

    def testInvalidParsing(self):
        self.assertRaises(Exception, P.Result.parse, '{"message": "Fine"}')
        self.assertRaises(Exception, P.Result.parse,
                          '{"status": %d}' % P.Result.OK)
        self.assertRaises(Exception, P.Result.parse, '{"status": -1}')
        self.assertRaises(Exception, P.Result.parse, '{"message": 123}')

    def testJsonDumping(self):
        FINE = 'fine'
        r = P.Result(P.Result.OK, FINE)
        js = r.json()

        resultDict = json.loads(js)
        self.assertIn(P.Result.STATUS, resultDict)
        self.assertEqual(resultDict[P.Result.STATUS], P.Result.OK)
        self.assertEqual(resultDict[P.Result.MESSAGE], FINE)

