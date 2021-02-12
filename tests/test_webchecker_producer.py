"""
Tests for the webchecker producer
"""
from unittest import IsolatedAsyncioTestCase
import json
from contextlib import asynccontextmanager
import aiohttp.client_exceptions

from aiokafka import AIOKafkaConsumer

from webcheck import WebCheckerProducer


KAFKA_SERVERS = ['kafka-1:9092', 'kafka-2:9092', 'kafka-3:9092']


class WebCheckerProducerTest(IsolatedAsyncioTestCase):
    """Test for WebCheckerProducer"""

    async def asyncSetUp(self):
        """Async setup"""
        self.consumer = AIOKafkaConsumer(
            'webchecker', bootstrap_servers=KAFKA_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')))
        await self.consumer.start()

    async def asyncTearDown(self):
        """Async tear down"""
        await self.consumer.stop()

    async def test_initialize(self):
        """Checks class initialization"""
        webchecker_producer = WebCheckerProducer("http://google.com", KAFKA_SERVERS)
        try:
            await webchecker_producer.init()
        finally:
            await webchecker_producer.stop()

    @asynccontextmanager
    async def webchecker_producer_test(self, webpage_url, regex=None):
        """Helper for building the test cases"""
        webchecker_producer = WebCheckerProducer(webpage_url, KAFKA_SERVERS, regex)
        try:
            await webchecker_producer.init()
            await webchecker_producer.check()
            async for msg in self.consumer:
                yield msg
                break
        finally:
            await webchecker_producer.stop()

    async def test_do_check_ok_without_regex(self):
        """Checks the website ok without a regex pattern"""
        webpage_url = 'https://google.com'
        async with self.webchecker_producer_test(webpage_url) as msg:
            value = msg.value[webpage_url]
            self.assertIsNone(value['content_check'])
            self.assertEqual(value['status_code'], 200)
            self.assertLessEqual(value['response_time'], 3)

    async def test_do_check_ok_with_regex_ok(self):
        """Checks the website ok with a matched regex"""
        webpage_url = 'http://google.com'
        async with self.webchecker_producer_test(webpage_url, 'google') as msg:
            value = msg.value[webpage_url]
            self.assertTrue(value['content_check'])
            self.assertEqual(value['status_code'], 200)
            self.assertLessEqual(value['response_time'], 3)

    async def test_do_check_ok_with_regex_no_ok(self):
        """Checks the website ok with a non matched regex"""
        webpage_url = 'http://google.com'
        async with self.webchecker_producer_test(webpage_url, 'microsoft') as msg:
            value = msg.value[webpage_url]
            self.assertFalse(value['content_check'])
            self.assertEqual(value['status_code'], 200)
            self.assertLessEqual(value['response_time'], 3)

    async def test_do_check_non_existent_webpage_without_regex(self):
        """Checks a non existent webpage"""
        webpage_url = 'http://awebpagethatwontexistever.noway.wanttobesureaboutit'
        with self.assertRaises(aiohttp.client_exceptions.ClientConnectorError):
            async with self.webchecker_producer_test(webpage_url):
                pass

    async def test_do_check_status_no_ok_without_regex(self):
        """Checks the website without a regex and status code != 20x"""
        webpage_url = 'https://theip.me/page-not-found'
        async with self.webchecker_producer_test(webpage_url) as msg:
            value = msg.value[webpage_url]
            self.assertIsNone(value['content_check'])
            self.assertEqual(value['status_code'], 404)
            self.assertLessEqual(value['response_time'], 3)
