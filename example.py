from whatisfacebook import FacebookGraphqlScraper

fb = FacebookGraphqlScraper()
result = fb.get_user_posts("Theanh28", days_limit=3)
print(result)
