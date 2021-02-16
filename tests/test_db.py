from unittest import IsolatedAsyncioTestCase
import datetime

from db import WebCheckerDB


class WebCheckerDBTest(IsolatedAsyncioTestCase):
    """Test for WebCheckerDB"""

    def setUp(self):
        """New db connection per test"""
        self.db = WebCheckerDB(host='postgres', database='webchecker',
                               user='postgres', password='webchecker')

    async def asyncTearDown(self):
        """Close db connection"""
        await self.db.close()

    async def asyncSetUp(self):
        """Initialize db connection"""
        await self.db.init()

    async def test_insert_entry(self):
        """Instert a new entry into the DB"""
        data = {
            'http://localhost': {
                'status_code': 200,
                'content_check': True,
                'response_time': 0.24343,
                'queried_at': datetime.datetime.utcnow().isoformat(),
            },
        }
        await self.db.insert_entry(data)
