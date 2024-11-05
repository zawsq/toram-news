import asyncio
import logging
from datetime import datetime

import aiohttp
import tzlocal
from lxml.html import fromstring
from rich.logging import RichHandler
from rich.traceback import install

from toram.config import config
from toram.database import MongoDB
from toram.utils import HTTPServer, Scraper

install(show_locals=True)

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)


class ToramListener:
    def __init__(self) -> None:
        self.base_url = "https://en.toram.jp/information/?type_code=all"
        self.base_selector = "#news > div.useBox > ul > li > a"
        self.request_interval = 300
        self.local_tz = tzlocal.get_localzone()
        self.mongo_db = MongoDB()
        self.scraper = Scraper()

    async def check_latest_news(self) -> list[str]:
        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session,
            session.get(url=self.base_url) as resp,
        ):
            parse_text = fromstring(await resp.text())

        latest_news = parse_text.cssselect(self.base_selector)
        news_ids = []
        for i in latest_news:
            news_date = i.cssselect("div > div.newsCategoryInner > p > time")[0].text_content().strip()
            compare_date = datetime.strptime(news_date, "%Y-%m-%d").replace(tzinfo=self.local_tz).date()

            current_date = datetime.now(tz=self.local_tz).date()

            if compare_date == current_date:
                news_ids.append(i.get("href").split("=")[-1])

        return news_ids[::-1]

    async def start_polling(self) -> None:
        while True:
            latest_news_ids = await self.check_latest_news()
            last_news_id = await self.mongo_db.fetch_last_news()

            news_ids_to_send = (
                latest_news_ids[latest_news_ids.index(last_news_id) + 1 :]
                if last_news_id in latest_news_ids
                else latest_news_ids
            )

            if not news_ids_to_send:
                logging.info("no news detected, sleeping...")
                await asyncio.sleep(self.request_interval)
                continue

            successfully_ids = []
            for i in news_ids_to_send:
                scrape_news_id = await self.scraper.get_toram_news(i)
                send_webhook_status = await self.scraper.send_webhook(
                    webhook_url=config.WEBHOOK_URL,
                    news_data=scrape_news_id,
                )

                if send_webhook_status == 200:  # noqa: PLR2004
                    successfully_ids.append(i)

            if successfully_ids:
                await self.mongo_db.update_news_id(news_id=successfully_ids[-1])

            await asyncio.sleep(self.request_interval)


async def main() -> None:
    toram_listener = ToramListener()
    background_tasks = set()
    task = None
    if config.HTTP_SERVER:
        http_server = HTTPServer(host=config.HOSTNAME, port=config.PORT)
        task = asyncio.create_task(http_server.run_server())
        background_tasks.add(task)

    await toram_listener.start_polling()

    if task:
        task.add_done_callback(background_tasks.discard)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt stopping polling")
