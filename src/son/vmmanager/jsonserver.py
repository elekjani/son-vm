from twisted.internet.protocol import Protocol
from twisted.internet.protocol import Factory

import logging
import json

class IJsonProcessor(object):

    class Result(object):

        OK = 1
        FAILED = 2
        UNKNOWN = 3
        STATUS_FIELDS = [OK, FAILED, UNKNOWN]

        STATUS = 'status'
        MESSAGE = 'message'

        def __init__(self, status, message, args = None):
            if status is None or message is None:
                raise Exception('Status and message is required'
                                'to create a result object')

            if status not in self.STATUS_FIELDS:
                raise Exception('Status must be on of the Result.OK,'
                                'Result.FAILED, Result.UNKNOWN fields.'
                                '(actual status: %s)' % status)

            if type(message) is not str:
                raise Exception('Message must be a string.'
                                '(actual type: %s)' % type(message))

            if args is not None and type(args) is not dict:
                raise Exception('Additional argument must be a dict.'
                                '(actual type: %s)' % type(args))

            self.status = status
            self.message = message
            self.args = args

        def json(self):
            result = { self.STATUS: self.status, self.MESSAGE: self.message }
            if self.args is not None:
                result.update(self.args)

            return json.dumps(result)

        @classmethod
        def parse(cls, jsonString):
            jsonDict = json.loads(jsonString)

            if cls.STATUS not in jsonDict:
                raise Exception('Invalid JSON: No %s field', cls.STATUS)

            if cls.MESSAGE not in jsonDict:
                raise Exception('Invalid JSON: No %s field', cls.MESSAGE)

            status = jsonDict.pop(cls.STATUS)

            if status not in cls.STATUS_FIELDS:
                raise Exception('Invalid %s: %s', cls.STATUS, status)

            message = jsonDict.pop(cls.MESSAGE)

            if type(message) is not str:
                raise Exception('Invalid %s: %s', cls.MESSAGE, message)

            if len(jsonDict) > 0:
                return cls(status, message, jsonDict)
            else:
                return cls(status, message)


    def process(self, json):
        pass


class JsonMsgReaderFactory(Factory):
    def __init__(self):
        self.logger = logging.getLogger(JsonMsgReader.__name__)
        self.processors = []

    def addProcessor(self, processorName, jsonProcessor):
        if not issubclass(type(jsonProcessor), IJsonProcessor):
            self.logger.error('Unable to add message processor with type: '
                              '%s', type(jsonProcessor))
            raise Exception('Invalid processor is given')

        self.processors.append((processorName, jsonProcessor))
        self.logger.info('Added processor: %s (%s)', processorName,
                         jsonProcessor.__class__.__name__)

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
        self._data += data.decode('utf-8')
        self.logger.debug("New data from %s: %s", self.transport.getPeer(), self._data)
        for js in self._get_complete_jsons_():
            results = {}
            for name, instance in self.processors:
                self.logger.debug("Passing JSON %s to precessor %s", js, name)
                result = instance.process(js)
                if isinstance(result, IJsonProcessor.Result):
                    results[name] = result.json()
                else:
                    r = IJsonProcessor.Result(IJsonProcessor.Result.UNKNOWN,
                                              'Processor returned with invalid result',
                                              {'RETURN_TYPE': str(type(result))})
                    results[name] = r.json()

            self.transport.write(json.dumps(results).encode('utf-8'))

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



