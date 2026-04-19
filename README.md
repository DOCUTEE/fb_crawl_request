# whatisfacebook

Scrape public Facebook posts without login using a simple, requests-based scraper.

This project is a streamlined fork developed from the foundational work at [FaustRen/facebook-graphql-scraper](https://github.com/FaustRen/facebook-graphql-scraper).

## Improvements
- **Lightweight:** Uses only `requests` to fetch user posts—no browser, Selenium, or Playwright required.
- **Focused:** Removed login-dependent features to focus exclusively on public page scraping.
- **Efficient:** Optimized for speed and minimal dependency overhead.

## Install

```bash
pip install whatisfacebook
```

## Quick Example

```python
from whatisfacebook import FacebookGraphqlScraper

# Initialize the scraper
fb = FacebookGraphqlScraper()

# Get posts from a specific username with a day limit
result = fb.get_user_posts("honghotduongpho.official00", days_limit=3)

for post in result["data"]:
    print(f"Content: {post['content']}")
    print(f"Likes: {post['reaction_count']}")
    print(f"Shares: {post['share_count']}")
    print(f"Comments: {post['comment_count']}")
    print("-" * 20)
```

## Results
The result object returns a structured dictionary containing profile info and a list of post data:
```json
{
    "fb_username_or_userid": "Theanh28",
    "profile": ["Theanh28 Entertainment | Hanoi"],
    "data": [
        {
            "post_id": "1280910250890741",
            "post_url": "https://www.facebook.com/1280910250890741",
            "profile_name": "Theanh28 Entertainment",
            "profile_short_name": "Theanh28 Entertainment",
            "profile_id": "100069153349307",
            "profile_url": "https://www.facebook.com/100069153349307",
            "permalink": "https://www.facebook.com/reel/2132682674109999/",
            "content": "Đâu sẽ là phù hợp nhất ",
            "hashtags": [],
            "post_type": "StoryAttachmentVideoStyleRenderer",
            "number_of_media": 1,
            "media_items": [
                {
                    "id": "2132682674109999",
                    "type": "Video",
                    "thumbnail_url": "https://scontent.fsgn2-5.fna.fbcdn.net/...",
                    "video_url": "https://video.fsgn2-8.fna.fbcdn.net/..."
                }
            ],
            "creation_time": 1776095067,
            "published_at": "2026-04-13T22:44:27",
            "published_date": "2026-04-13",
            "reaction_count": 976,
            "share_count": 10,
            "comment_count": 39,
            "sub_reactions": [
                {"id": "1635855486666999", "name": "Thích", "reaction_count": 598},
                {"id": "115940658764963", "name": "Haha", "reaction_count": 362},
                {"id": "1678524932434102", "name": "Yêu thích", "reaction_count": 9},
                {"id": "908563459236466", "name": "Buồn", "reaction_count": 4},
                {"id": "478547315650144", "name": "Wow", "reaction_count": 2},
                {"id": "613557422527858", "name": "Thương thương", "reaction_count": 1}
            ]
        }
    ]
}
```

## Extracting Additional Data

> **Note:** If you need more data fields than what's provided in `data`, you can manually extract additional information from `raw_data`. This contains the complete raw Facebook GraphQL API responses.

```python
result = fb.get_user_posts("page_username", days_limit=3)

# Access raw API responses for custom data extraction
for raw_response in result["raw_data"]:
    # Extract any custom fields you need
    custom_field = raw_response.get("your_custom_field")
```

## Credits

Thank you to the original project owner [FaustRen](https://github.com/FaustRen) and the [facebook-graphql-scraper](https://github.com/FaustRen/facebook-graphql-scraper) repository for the foundational work that made this simplified version possible.
