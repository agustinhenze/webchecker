import asyncpg
import datetime


TABLES_DB = (
    """
    CREATE TABLE IF NOT EXISTS webpage (
        id serial PRIMARY KEY,
        url VARCHAR ( 255 ) UNIQUE NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS webcheck (
        id serial PRIMARY KEY,
        webpage_id INT NOT NULL,
        FOREIGN KEY (webpage_id) REFERENCES webpage (id),
        response_time DOUBLE PRECISION NOT NULL,
        content_check BOOLEAN,
        queried_at TIMESTAMPTZ NOT NULL
    );
    """,
)


class WebCheckerDB:
    """Save data from kafka into a postgres db"""

    def __init__(self, host, database, user, password):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.conn = None
        self.cache = {}

    async def init(self):
        """
        Initialize database connection and create the database schema if it doesn't
        exist.
        """
        self.conn = await asyncpg.connect(
            user=self.user, password=self.password, database=self.database,
            host=self.host)
        for cmd in TABLES_DB:
            await self.conn.execute(cmd)

    async def close(self):
        """Close dabatase connection"""
        await self.conn.close()

    async def _get_webpage_id(self, url):
        """Get the webpage_id from cache otherwise it fetches it from the DB"""
        webpage_id = self.cache.get(url, None)
        if webpage_id is None:
            row = await self.conn.fetchrow('SELECT * FROM webpage WHERE url = $1', url)
            if row:
                webpage_id = row['id']
                self.cache[url] = webpage_id
        return webpage_id

    async def insert_entry(self, data):
        """Insert the data into the database"""
        for url in data.keys():
            webpage_id = await self._get_webpage_id(url)
            if webpage_id is None:
                await self.conn.execute('INSERT INTO webpage(url) VALUES($1)', url)
                webpage_id = await self._get_webpage_id(url)
            entry = data[url]
            await self.conn.execute(
                'INSERT INTO webcheck(webpage_id, response_time, content_check, '
                'queried_at) VALUES($1, $2, $3, $4)',
                webpage_id, entry['response_time'], entry['content_check'],
                datetime.datetime.fromisoformat(entry['queried_at']))

    async def insert_kafka_batch(self, batch_data):
        """Insert batche messages from kafka into the database"""
        async with self.conn.transaction():
            for data in batch_data:
                await self.insert_entry(data.value)
