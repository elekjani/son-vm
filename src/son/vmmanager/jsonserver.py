from twisted.internet.protocol import Protocol
from twisted.internet.protocol import Factory

import logging
import json

class IJsonProcessor(object):
    def process(self, json):
        pass


class JsonMsgReaderFactory(Factory):

    def __init__(self):
        self.logger = logging.getLogger(JsonMsgReader.__name__)
        self.processors = []

    def addProcessor(self, jsonProcessor):
        if not issubclass(type(jsonProcessor), IJsonProcessor):
            self.logger.error('Unable to add message processor with type: %s', type(jsonProcessor))
            raise Exception('Invalid processor is given')

        self.processors.append(jsonProcessor)
        self.logger.info('Added processor: ' + jsonProcessor.__class__.__name__)

    def buildProtocol(self, addr):
        return JsonMsgReader(self.processors)


class JsonMsgReader(Protocol):

    def __init__(self, jsonProcessors = []):
        self.logger = logging.getLogger(JsonMsgReader.__name__)
        self.processors = jsonProcessors

    def connectionMade(self):
        self.logger.info("New connection from %s", self.transport.getPeer())
        self._data = ""

    def dataReceived(self, data):
        self._data += data
        self.logger.debug("New data from %s: %s", self.transport.getPeer(), self._data)
        for js in self._get_complete_jsons_():
            for p in self.processors:
                self.logger.debug("Passing JSON %s to precessor %s", js, p.__class__.__name__)
                p.process(js)

    def _get_json_segments_(self, jsonString):
        # Let's hope that there is no '{' or '}' in any string data
        # of the JSON...
        boundaries = 0
        start = -1
        segments = []
        for i in range(0, len(jsonString)):
            if jsonString[i] == '{':
                if start == -1:
                    start = i
                    boundaries = 1
                else:
                    boundaries += 1

            if jsonString[i] == '}':
                if start != -1:
                    boundaries -= 1

            if start != -1 and boundaries == 0:
                segments.append({ 'start': start, 'end': i })
                start = -1

        return segments

    def _get_complete_jsons_(self):
        jsons = []
        self.logger.debug("Checking data for socket %s", self._data)
        segments = self._get_json_segments_(self._data)
        self.logger.debug("Found %d segment(s)", len(segments))
        for s in segments:
            subJsonString = self._data[s['start']:s['end']+1]
            self.logger.debug("Parsing %s at %d-%d", subJsonString, s['start'], s['end']+1)
            try:
                js = json.loads(subJsonString)
                jsons.append(js)
            except json.decoder.JSONDecodeError as e:
                self.logger.error("Unable to parse JSON message. Ignoring it!")
                self.logger.error("\tJSON message: %s", subJsonString)
                self.logger.error("\tDecoding error: %s", e.msg)

            if len(segments) > 0:
                end = segments.pop()['end'] + 1
                self._data = self._data[end:]

        return jsons



