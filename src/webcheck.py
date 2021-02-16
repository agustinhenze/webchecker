"""
Checks a website and records this into a Postgres DB via kafka.
"""
import os
import sys
import logging
import time
import re
import argparse
import asyncio
import json
import datetime
import configparser

import aiohttp
import aiokafka

from db import WebCheckerDB

logger = logging.getLogger(__name__)


class WebCheckerProducer:
    """Checks a website and publish the result through kafka"""

    def __init__(self, weburl, kafka_servers, regex=None):
        self.weburl = weburl
        self.kafka_servers = kafka_servers
        self.regex = regex
        self.producer = None

    async def init(self):
        """Initialize kafka producer"""
        logger.info("Initializing WebCheckerProducer")
        self.producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=self.kafka_servers,
            value_serializer=lambda m: json.dumps(m).encode('ascii'))
        await self.producer.start()

    async def stop(self):
        """Flush and stop kafka producer"""
        logger.info("Stopping WebCheckerProducer")
        await self.producer.flush()
        await self.producer.stop()

    async def publish_result(self, status_code, response_time, content, queried_at):
        """Publish to kafka the web check results"""
        data = {
            self.weburl: {
                'status_code': status_code,
                'response_time': response_time,
                'content_check': self._check_content(content),
                'queried_at': queried_at,
            }
        }
        logger.debug("Data published %r", data)
        await self.producer.send_and_wait('webchecker', data)

    async def check(self):
        """Do a request GET to the web page and publish the result to kafka"""
        async with aiohttp.ClientSession() as session:
            start = time.monotonic()
            queried_at = datetime.datetime.utcnow().isoformat()
            async with session.get(self.weburl) as response:
                content = await response.text()
                end = time.monotonic()
                await self.publish_result(
                    response.status, end - start, content, queried_at)
                return content

    def _check_content(self, content):
        """Check if the regex pattern is found in the content of the webpage"""
        if self.regex:
            return bool(re.search(self.regex, content, re.MULTILINE))
        return None


class WebCheckerConsumer:
    """Listen on a kafka topic and submit the data received into a postgres db"""

    def __init__(self, kafka_servers, postgres_cfg):
        self.kafka_servers = kafka_servers
        self.db_host = postgres_cfg['host']
        self.db_name = postgres_cfg['database']
        self.db_user = postgres_cfg['user']
        self.db_password = postgres_cfg['password']
        self.consumer = None
        self.webchecker_db = None

    async def init(self):
        """Initialize kafka producer"""
        logger.info("Initializing WebCheckerConsumer")
        self.consumer = aiokafka.AIOKafkaConsumer(
            'webchecker', bootstrap_servers=self.kafka_servers, group_id="webchecker",
            value_deserializer=lambda m: json.loads(m.decode('utf-8')))
        self.webchecker_db = WebCheckerDB(host=self.db_host, database=self.db_name,
                                          user=self.db_user, password=self.db_password)
        await self.consumer.start()
        await self.webchecker_db.init()

    async def receive_messages(self, timeout_s=10):
        """Receive a batch of messages and then insert them into the postgres db."""
        result = await self.consumer.getmany(timeout_ms=timeout_s * 1000)
        for _, messages in result.items():
            if messages:
                logger.debug("Batch messages received %r", messages)
                await self.webchecker_db.insert_kafka_batch(messages)

    async def stop(self):
        """Stop the kafka consumer and close the webchecker db"""
        await self.consumer.stop()
        await self.webchecker_db.close()


async def webchecker_consumer_run(args):
    """Run the web checker consumer"""
    config = configparser.ConfigParser()
    config.read(args.postgres_config)
    webchecker_consumer = WebCheckerConsumer(args.kafka_url, config['postgres'])
    await webchecker_consumer.init()
    while True:
        await webchecker_consumer.receive_messages()
    await webchecker_consumer.stop()


async def webchecker_producer_run(args):
    """Run the web checker producer periodically"""
    interval_s = args.interval
    webchecker_producer = WebCheckerProducer(args.website, args.kafka_url,
                                             args.regex_check)
    await webchecker_producer.init()
    start_time = time.monotonic()
    while True:
        elapsed_time = round(time.monotonic() - start_time)
        logger.debug('Checking website %s %d', args.website, elapsed_time)
        await asyncio.gather(
            asyncio.sleep(interval_s),
            webchecker_producer.check(),
        )


def parse_arguments(args):
    """Parse arguments"""
    parser = argparse.ArgumentParser(
        description="Checks periodically a web site passed as parameter")
    subparser = parser.add_subparsers(
        help="Sub-commands", dest='subcmd')
    consumer_parser = subparser.add_parser(
        "consumer", help="Receives data from kafka and saves data into db")
    consumer_parser.add_argument('-p', '--postgres-config', type=str, required=True,
                                 help='Path to the postgres configuration %(default)s',
                                 default='./postgres.ini')
    producer_parser = subparser.add_parser(
        "producer", help="Performs a GET request and submits data to kafka")
    producer_parser.add_argument('-w', '--website', type=str, required=True,
                                 help="Website to be checked, e.g. https://theip.me")
    producer_parser.add_argument('-r', '--regex-check', type=str,
                                 help="Regex for checking the pattern in the webpage "
                                 "content.")
    producer_parser.add_argument('-i', '--interval', type=int, default=10,
                                 help="Interval (seconds) for every check. Default: "
                                 "%(default)s")
    parser.add_argument('-k', '--kafka-url', action='append', required=True,
                        help='Kafka url, it can be passed multiple times, e.g. '
                        '--kafka-url localhost:9092')
    return parser.parse_args(args)


def main():
    """Main function"""
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))
    args_parsed = parse_arguments(sys.argv[1:])
    if args_parsed.subcmd == 'producer':
        asyncio.run(webchecker_producer_run(args_parsed))
    elif args_parsed.subcmd == 'consumer':
        asyncio.run(webchecker_consumer_run(args_parsed))


if __name__ == '__main__':
    main()
