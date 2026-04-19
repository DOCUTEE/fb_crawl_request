from whatisfacebook import FacebookGraphqlScraper

fb = FacebookGraphqlScraper()
result = fb.get_user_posts("Theanh28", days_limit=1)

import json
with open("result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False)