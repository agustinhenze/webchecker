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

import aiohttp
import aiokafka

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
        self.producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=self.kafka_servers,
            value_serializer=lambda m: json.dumps(m).encode('ascii'))
        await self.producer.start()

    async def stop(self):
        """Flush and stop kafka producer"""
        await self.producer.flush()
        await self.producer.stop()

    async def publish_result(self, status_code, response_time, content):
        """Publish to kafka the web check results"""
        data = {
            self.weburl: {
                'status_code': status_code,
                'response_time': response_time,
                'content_check': self._check_content(content),
            }
        }
        logger.debug("Data published %r", data)
        await self.producer.send_and_wait('webchecker', data)

    async def check(self):
        """Do a request GET to the web page and publish the result to kafka"""
        async with aiohttp.ClientSession() as session:
            start = time.monotonic()
            async with session.get(self.weburl) as response:
                content = await response.text()
                end = time.monotonic()
                await self.publish_result(response.status, end - start, content)
                return content

    def _check_content(self, content):
        """Check if the regex pattern is found in the content of the webpage"""
        if self.regex:
            return bool(re.search(self.regex, content, re.MULTILINE))
        return None


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
        "Checks periodically a web site passed as parameter")
    parser.add_argument('-k', '--kafka-url', action='append', required=True,
                        help='Kafka url, it can be passed multiple times, e.g. '
                        '--kafka-url localhost:9092')
    parser.add_argument('-w', '--website', type=str, required=True,
                        help="Website to be checked, e.g. https://theip.me")
    parser.add_argument('-r', '--regex-check', type=str,
                        help="Regex for checking the pattern in the webpage content.")
    parser.add_argument('-i', '--interval', type=int, default=10,
                        help="Interval (seconds) for every check. Default: %(default)")
    return parser.parse_args(args)


def main():
    """Main function"""
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    logger.setLevel(os.environ.get('LOG_LEVEL', 'WARNING'))
    args_parsed = parse_arguments(sys.argv[1:])
    asyncio.run(webchecker_producer_run(args_parsed))


if __name__ == '__main__':
    main()
