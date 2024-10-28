import re
from typing import Any

import aiohttp
from discord_webhook import AsyncDiscordWebhook, DiscordEmbed
from lxml.etree import Comment
from lxml.html import fromstring


class Scraper:
    def __init__(self) -> None:
        self.title_attr = "delux"
        self.skip_src = {"#top"}
        self.attrib_classes = {"smallTitle news_title yellow": "Title"}
        self.skip_key = {"Note"}

    async def get_toram_news(self, news_id: str) -> dict[str, str]:
        url = f"https://en.toram.jp/information/detail/?information_id={news_id}"
        async with (
            aiohttp.ClientSession() as session,
            session.get(url=url, ssl=False) as resp,
        ):
            parse_text = fromstring(await resp.text())

        news_info = parse_text.cssselect("#news > div")[0]
        news_datas = {"Title": ""}
        general_datas = {}

        for i in news_info.iter():
            attrib = i.attrib

            if i.tag in {"script", Comment}:
                continue

            if attrib.get("class") and attrib["class"].startswith(self.title_attr):
                news_datas[i.text] = ""
            elif attrib.get("class") and attrib["class"] in self.attrib_classes:
                general_datas[self.attrib_classes[attrib["class"]]] = i.text_content().strip()
            else:
                pagination = list(news_datas.keys())[-1]
                text = (i.text or "").strip()
                tail = (i.tail or "").strip()

                if link := attrib.get("href"):
                    if link in self.skip_src:
                        continue
                    link = link.replace("//", "https://").replace("#", f"{url}#")
                    content = f"[{text}]({link}) {tail}" if text else f"{link} {tail}"
                elif attrib.get("src"):
                    content = (attrib.get("src") or "").strip()
                else:
                    content = f" {text}{tail}" if i.tag == "span" else f"\n{text}{tail}"

                news_datas[pagination] += content

        title = general_datas["Title"]
        old_key = "Title"
        return {title if k == old_key else k: v for k, v in news_datas.items()}

    async def send_webhook(self, webhook_url: str, news_data: dict[str, str]) -> Any:  # noqa: ANN401
        webhook = AsyncDiscordWebhook(url=webhook_url)
        image_pattern = r"https?://[^\s]+?\.(?:png|jpeg|jpg)"
        multi_image_pattern = r"(Lv.+?)\n\n(https?://[^\s]+?\.(?:png|jpeg|jpg))"

        for key, value in news_data.items():
            if key in self.skip_key:
                continue
            modified_value = value.replace('"', "**")

            image_matches = re.findall(image_pattern, modified_value)
            multi_image_matches = re.findall(multi_image_pattern, modified_value)

            if image_matches and not multi_image_matches:
                embed = DiscordEmbed(title=key)

                for index, image in enumerate(image_matches):
                    embed.set_image(url=image) if index == 0 else embed.set_thumbnail(image)
                    modified_value = modified_value.replace(image, "")

                embed.set_description(description=modified_value)
                webhook.add_embed(embed)
            elif len(image_matches) >= 1:
                for match in multi_image_matches:
                    embed = DiscordEmbed(title=match[0])
                    embed.set_image(url=match[1])
                    webhook.add_embed(embed)
            else:
                embed = DiscordEmbed(title=key, description=modified_value)
                webhook.add_embed(embed)

        return await webhook.execute()
