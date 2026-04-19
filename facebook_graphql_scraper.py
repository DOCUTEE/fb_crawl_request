# -*- coding: utf-8 -*-
import re
import requests
from datetime import datetime
from utils import *
from loguru import logger


class FacebookGraphqlScraper():
    def __init__(self):
        self.doc_id = "26420831597536910"
        self.raw_data = []
        self.creation_list = []
        self.logger = logger

    def get_user_id_from_username(self, username: str) -> tuple:
        if username.isdigit():
            return username, []

        url = f"https://www.facebook.com/{username}?locale=en_us"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        profile_feed = []
        try:
            response = requests.get(
                url, headers=headers, allow_redirects=True, timeout=10
            )
            # Look for user ID in page content
            patterns = [
                r'"userID":"(\d+)"',
                r'"actorID":"(\d+)"',
                r'"id":"(\d+)"',
                r'"profile_owner":"(\d+)"',
                r"entity_id=(\d+)",
                r'"owner":{"__typename":"User","id":"(\d+)"}',
            ]
            user_id = username
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    user_id = match.group(1)
                    print(f"Resolved '{username}' -> '{user_id}'")
                    break

            # Extract profile name
            name_patterns = [
                r'"name":"([^"]+)","__typename":"User"',
                r'"pageName":"([^"]+)"',
                r"<title>([^<]+)</title>",
            ]
            for pattern in name_patterns:
                match = re.search(pattern, response.text)
                if match:
                    name = match.group(1).replace(" | Facebook", "").strip()
                    if name:
                        profile_feed.append(name)
                        break

            # Extract followers count if available
            follower_patterns = [
                r"(\d+(?:[,.]\d+)?)\s*followers",
                r'"follower_count":(\d+)',
                r'"followers":\{"count":(\d+)\}',
            ]
            for pattern in follower_patterns:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    followers = match.group(1)
                    profile_feed.append(f"{followers} followers")
                    break

            return user_id, profile_feed

        except Exception as e:
            print(f"Error resolving user ID: {e}")
            return username, profile_feed

    def _safe_get(self, lst, index, default=None):
        """Safely get item from list by index"""
        return lst[index] if index < len(lst) else default

    def format_data(self, res_in, fb_username_or_userid, new_reactions):
        # Build result list without pandas
        final_res = []
        for i, post in enumerate(res_in):
            # Add computed fields directly to post dict
            post["context"] = self._safe_get(self.requests_parser.context_list, i, "")
            post["username_or_userid"] = fb_username_or_userid
            post["owing_profile"] = self._safe_get(
                self.requests_parser.owning_profile, i, {}
            )
            post["sub_reactions"] = self._safe_get(new_reactions, i, {})
            post["post_url"] = "https://www.facebook.com/" + post.get("post_id", "")

            # Convert timestamp to datetime
            time_val = self._safe_get(self.requests_parser.creation_list, i, 0)
            post["time"] = time_val
            dt = datetime.fromtimestamp(time_val)
            post["published_date"] = dt.isoformat()

            # Get enhanced data from raw node if available
            raw_node = self._safe_get(self.requests_parser.raw_nodes, i, {})
            story = deepget(raw_node, "comet_sections.content.story", {})
            comet_sections = deepget(raw_node, "comet_sections", {})

            # Extract content and hashtags
            content = self._safe_get(self.requests_parser.context_list, i, "")
            hashtags = self._extract_hashtags(content) if content else []

            # Extract media info
            media_info = self._extract_media_info(story, raw_node)

            # Extract engagement metrics from comet_sections (transformer paths)
            creation_time = deepget(comet_sections, "timestamp.story.creation_time")
            # Fallback: try story.creation_time directly
            if not creation_time:
                creation_time = story.get("creation_time")
            # Fallback: use time_val from parser
            if not creation_time and time_val:
                creation_time = time_val

            # Try multiple paths for comments and shares
            comments = None
            shares = None

            # Path 1: From comet_sections (transformer style)
            if comet_sections:
                comments = deepget(
                    comet_sections,
                    "feedback.story.story_ufi_container.story.feedback_context.feedback_target_with_context.comet_ufi_summary_and_actions_renderer.feedback.comment_rendering_instance.comments.total_count",
                )
                shares = deepget(
                    comet_sections,
                    "feedback.story.story_ufi_container.story.feedback_context.feedback_target_with_context.comet_ufi_summary_and_actions_renderer.feedback.share_count.count",
                )

            # Path 2: From post (nested style with deepget)
            if comments is None:
                comments = deepget(
                    post, "comment_rendering_instance.comments.total_count"
                )
            if shares is None:
                shares = deepget(post, "share_count.count")

            # Path 3: From raw_node feedback
            if comments is None or shares is None:
                feedback = deepget(raw_node, "feedback", {})
                if comments is None:
                    comments = deepget(
                        feedback, "comment_rendering_instance.comments.total_count"
                    )
                if shares is None:
                    shares = deepget(feedback, "share_count.count")

            # Extract author info from story.actors
            actor_url = None
            actor_id = None
            actors = story.get("actors", [])
            if actors and isinstance(actors[0], dict):
                actor_url = actors[0].get("url")
                actor_id = actors[0].get("id")

            # Get profile name from owing_profile
            profile_name = None
            owing_profile = post.get("owing_profile", {})
            if isinstance(owing_profile, dict):
                profile_name = owing_profile.get("name")
                # Fallback for actor_id from owing_profile
                if actor_id is None:
                    actor_id = owing_profile.get("id")
                # Build actor_url if missing
                if actor_url is None and actor_id:
                    actor_url = f"https://www.facebook.com/{actor_id}"

            # Format timestamps exactly like transformer
            if creation_time:
                dt = datetime.fromtimestamp(creation_time)
                published_at = dt.isoformat()
                published_date = dt.date().isoformat()
                timestamp = creation_time
            else:
                published_at = None
                published_date = None
                timestamp = None

            # Extract permalink_url with multiple fallback paths
            permalink_url = deepget(raw_node, "permalink_url")
            # Fallback: from timeline_list_feed_units structure
            if not permalink_url:
                permalink_url = deepget(
                    raw_node, "timeline_list_feed_units.edges.0.node.permalink_url"
                )
            # Fallback: from post directly
            if not permalink_url:
                permalink_url = post.get("permalink_url")
            # Fallback: from story
            if not permalink_url:
                permalink_url = story.get("permalink_url")
            # Fallback: from comet_sections
            if not permalink_url:
                permalink_url = deepget(comet_sections, "story.permalink_url")

            # Skip if no permalink (profile post, not real post)
            if not permalink_url:
                print(f"DEBUG: Skipping post {post.get('post_id')} - no permalink_url")
                print(
                    f"  raw_node type: {type(raw_node)}, keys: {list(raw_node.keys()) if isinstance(raw_node, dict) else 'N/A'}"
                )
                # Try to find permalink in raw_node
                if (
                    isinstance(raw_node, dict)
                    and "timeline_list_feed_units" in raw_node
                ):
                    tlfu = raw_node["timeline_list_feed_units"]
                    print(
                        f"  timeline_list_feed_units type: {type(tlfu)}, keys: {list(tlfu.keys()) if isinstance(tlfu, dict) else 'N/A'}"
                    )
                    if isinstance(tlfu, dict) and "edges" in tlfu:
                        edges = tlfu["edges"]
                        print(
                            f"  edges type: {type(edges)}, len: {len(edges) if isinstance(edges, list) else 'N/A'}"
                        )
                        if isinstance(edges, list) and len(edges) > 0:
                            first_edge = edges[0]
                            print(
                                f"  first_edge type: {type(first_edge)}, keys: {list(first_edge.keys()) if isinstance(first_edge, dict) else 'N/A'}"
                            )
                            if isinstance(first_edge, dict) and "node" in first_edge:
                                node = first_edge["node"]
                                print(
                                    f"  node type: {type(node)}, keys: {list(node.keys())[:10] if isinstance(node, dict) else 'N/A'}"
                                )
                                if isinstance(node, dict) and "permalink_url" in node:
                                    print(
                                        f"  FOUND permalink_url: {node['permalink_url']}"
                                    )
                continue

            # Select only needed fields (exactly match transformer)
            selected = {
                # Identity
                "post_id": post.get("post_id"),
                "post_url": post.get("post_url"),
                "permalink_url": permalink_url,
                # Author info
                "author_name": profile_name,
                "author_short_name": profile_name,
                "author_profile_id": actor_id,
                "author_profile_url": actor_url,
                # Content
                "content": content,
                "hashtags": hashtags,
                # Media/Attachments
                "post_type": media_info["type"],
                "number_of_media": media_info["count"],
                "media_items": media_info["items"],
                # Timestamps
                "published_at": published_at,
                "published_date": published_date,
                "timestamp": timestamp,
                # Engagement metrics
                "likes": self._parse_count(deepget(post, "reaction_count.count")),
                "comments": comments,
                "shares": shares,
                "sub_reactions": post.get("sub_reactions"),
            }

            # Filter: skip non-real posts (profile posts)
            # A real post should have: content OR media OR engagement (likes/comments/shares)
            has_content = content is not None and content.strip()
            has_media = media_info["count"] > 0
            has_engagement = (
                (selected["likes"] is not None and selected["likes"] > 0)
                or (comments is not None and comments > 0)
                or (shares is not None and shares > 0)
            )

            if has_content or has_media or has_engagement:
                final_res.append(selected)

        # Remove duplicates
        filtered_post_id = []
        filtered_data = []
        for each_data in final_res:
            if each_data["post_id"] not in filtered_post_id:
                filtered_data.append(each_data)
                filtered_post_id.append(each_data["post_id"])
        return filtered_data

    def _extract_hashtags(self, text: str) -> list:
        """Extract hashtags from text content."""
        if not text:
            return []
        hashtags = re.findall(r"#\w+", text)
        return list(set(hashtags))

    def _extract_media_info(self, story: dict, raw_node: dict = None) -> dict:
        """Extract media/attachment information including URLs."""
        attachments = story.get("attachments", [])
        media_items = []
        post_type = "No media"

        for att in attachments:
            styles = deepget(att, "styles.attachment", {}) if att.get("styles") else {}
            style_type = deepget(att, "styles.__typename")

            if style_type == "StoryAttachmentPhotoStyleRenderer":
                post_type = "Photo"
                node_media = styles.get("media", {})
                media_items.append(
                    {
                        "id": node_media.get("id"),
                        "type": node_media.get("__typename"),
                        "image_url": deepget(node_media, "photo_image.uri"),
                        "caption": node_media.get("accessibility_caption"),
                    }
                )
            elif style_type == "StoryAttachmentAlbumStyleRenderer":
                post_type = "Album"
                nodes = deepget(styles, "all_subattachments.nodes", [])
                for node in nodes:
                    node_media = node.get("media", {})
                    if node_media.get("__typename") == "Video":
                        media_items.append(
                            {
                                "id": node_media.get("id"),
                                "type": "Video",
                                "thumbnail_url": deepget(node_media, "image.uri"),
                                "video_url": deepget(
                                    node_media,
                                    "videoDeliveryLegacyFields.browser_native_hd_url",
                                ),
                            }
                        )
                    else:
                        media_items.append(
                            {
                                "id": node_media.get("id"),
                                "type": node_media.get("__typename"),
                                "image_url": deepget(node_media, "image.uri"),
                                "caption": deepget(node_media, "accessibility_caption"),
                            }
                        )
            elif style_type == "StoryAttachmentVideoStyleRenderer":
                post_type = "Video"
                node_media = deepget(att, "styles.attachment.media", {})
                media_items.append(
                    {
                        "id": node_media.get("id"),
                        "type": node_media.get("__typename"),
                        "thumbnail_url": deepget(node_media, "thumbnailImage.uri"),
                        "video_url": deepget(
                            node_media,
                            "videoDeliveryLegacyFields.browser_native_hd_url",
                        ),
                    }
                )

        return {"type": post_type, "count": len(media_items), "items": media_items}

    def _parse_count(self, value):
        """Safely parse count values to integers."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def process_reactions(self, res_in):
        reactions_out = []
        for each_res in res_in:
            each_reactions = each_res["top_reactions"]["edges"]
            processed_reactions = self.requests_parser.process_reactions(
                reactions_in=each_reactions
            )
            reactions_out.append(processed_reactions)
        return reactions_out

    def get_user_posts(
        self,
        fb_username_or_userid: str,
        days_limit: int = 61,
        display_progress: bool = True,
    ) -> dict:

        # Auto-resolve username to user ID and extract profile info
        user_id, profile_feed = self.get_user_id_from_username(fb_username_or_userid)

        print(f"Collecting posts for {user_id} (doc_id: {self.doc_id})")
        print(f"Profile info: {profile_feed}")

        result = self.requests_flow(
            doc_id=self.doc_id,
            fb_userid=user_id,
            days_limit=days_limit,
            display_progress=display_progress,
        )
        return {
            "fb_username_or_userid": fb_username_or_userid,
            "profile": profile_feed,
            "data": result,
            "raw_data": self.raw_data,
        }

    def find_main_data(self, json_data):
        if "comet_sections" in json_data.get("data", {}).get("node", {}):
            return json_data["data"]["node"]
        return json_data["data"]["node"]["timeline_list_feed_units"]["edges"][0]["node"]

    def extract_hashtags(self, text):
        return re.findall(r"#\w+", text)

    def extract_media_info(self, story: dict) -> dict:
        """
        Extract media/attachment information including URLs.
        
        Handles 3 styles:
        - Photo: styles.attachment.media.photo_image.uri
        - Video: styles.attachment.media.video_image.uri
        - Album: styles.attachment.all_subattachments.nodes[].media.image.uri
        """

        attachments = story.get("attachments", [])
        media_items = []
        
        # self.logger.debug(f"Processing attachments: {attachments}")
        post_item = {
            "id": story["post_id"],
            "type": "No media"
        }
        for att in attachments:
            # self.logger.debug(f"Processing attachment: {att}")
            media = deepget(att, "media", {})
            styles = deepget(att, "styles.attachment", {}) if att.get("styles") else {}
            
            post_item = {
                "id": media.get("id"),
                "type": deepget(att, "styles.__typename"),  # Photo, Video, etc.
            }
            media_items = []
            if styles:
                # self.logger.debug(f"Processing attachment: {att}")
                # Method 1: Single photo
                if post_item["type"] == "StoryAttachmentPhotoStyleRenderer":
                    self.logger.debug(f"Processing in method 1: Photo")
                    node_media = styles.get("media", {})
                    # self.logger.debug(f"Node media: {node_media}")
                    media_items.append({
                        "id": node_media["id"],
                        "type": node_media["__typename"],
                        "image_url": node_media["photo_image"]["uri"],
                        "caption": node_media.get("accessibility_caption")
                    })
                
                # Method 2: Album style - all_subattachments.nodes[].media.image.uri
                if post_item["type"] == "StoryAttachmentAlbumStyleRenderer":
                    nodes = deepget(styles, "all_subattachments.nodes", [])
                    for node in nodes:
                        node_media = node.get("media", {})
                        # Check for video thumbnail in album
                        if node_media["__typename"] == "Video":
                            thumb = node_media["image"]["uri"]
                            video_url = deepget(node_media, "video_grid_renderer.video.videoDeliveryLegacyFields.browser_native_hd_url")
                            media_items.append({
                                "id": node_media.get("id"),
                                "type": node_media.get("__typename"),
                                "thumbnail_url": thumb,
                                "video_url": video_url,
                            })
                        else:
                            # Check for photo
                            image_url = deepget(node_media, "image.uri")
                            caption = deepget(node_media, "accessibility_caption")
                            media_items.append({
                                "id": node_media.get("id"),
                                "type": node_media.get("__typename"),
                                "image_url": image_url,
                                "caption": caption,
                            })

                # Method 3: Video
                if post_item["type"] == "StoryAttachmentVideoStyleRenderer":
                    self.logger.debug(f"Processing in method 3: Video")
                    node_media = att["styles"]["attachment"]["media"]
                    # $.data.raw_data[1].data.node.attachments[0].styles.attachment.media.videoDeliveryLegacyFields.browser_native_hd_url
                    # self.logger.debug(f"Media: {node_media}")
                    media_type = node_media["__typename"]
                    video_url = node_media["videoDeliveryLegacyFields"]["browser_native_hd_url"]
                    thumbnail_url = node_media["thumbnailImage"]["uri"]
                    media_items.append(
                        {
                            "id": node_media["id"],
                            "type": media_type,
                            "thumbnail_url": thumbnail_url,
                            "video_url": video_url,
                        }
                    )
        
        return {
            "id": post_item["id"],
            "type": post_item["type"], # Photo, Album, Video, etc.
            "count": len(media_items),
            "items": media_items,
        }

    def process_reactions(self, top_reactions):
        number_of_reactions = top_reactions["count"]
        elements = top_reactions["edges"]
        reactions = []
        for i in range(number_of_reactions):
            stat = {}
            element = elements[i]
            stat["id"] = element["node"]["id"]
            stat["name"] = element["node"]["localized_name"]
            stat["reaction_count"] = element["reaction_count"]
            reactions.append(stat)
        return reactions
    def extract_raw_data(self, body_content):
        extracted_data = []
        for each_body in body_content:
            json_data = json.loads(each_body)
            self.raw_data.append(json_data)
            # data.node.timeline_list_feed_units.edges[0].node
            # with open("json_data.json", "w") as f:
            #     json.dump(json_data, f, indent=4)
            if not json_data.get("data",{}).get("node",{}):
                self.logger.warning("No node found in data")
                continue
            main_data = self.find_main_data(json_data)
            
            post_id = main_data["post_id"]
            post_url = f"https://www.facebook.com/{post_id}"
            
            # with open("main_data.json", "w") as f:
            #     json.dump(main_data, f)
            permalink = main_data["permalink_url"]
            owning_profile = main_data["feedback"]["owning_profile"]
            profile_name = owning_profile["name"]
            profile_short_name = owning_profile["short_name"]
            profile_id = owning_profile["id"]
            profile_url = f"https://www.facebook.com/{profile_id}"

            comet_sections = main_data["comet_sections"]
            creation_time = comet_sections["timestamp"]["story"]["creation_time"]
            
            # with open("comet_sections.json", "w") as f:
            #     json.dump(comet_sections, f)
            
            content = comet_sections["content"]["story"]["message"]["text"]
            hashtags = self.extract_hashtags(content)

            story = comet_sections["content"]["story"]
            # comet_sections.timestamp.story.creation_time
            self.creation_list.append(creation_time)
            media_info = self.extract_media_info(story)
            post_type = media_info["type"]
            number_of_media = media_info["count"]
            media_items = media_info["items"]

            published_at = datetime.fromtimestamp(creation_time).isoformat()  # ISO format: 2026-03-31T06:12:31
            published_date = datetime.fromtimestamp(creation_time).date().isoformat()  # Date only: 2026-03-31
            

            # $.raw_data[0].data.node.timeline_list_feed_units.edges[0].node.comet_sections.feedback.story.story_ufi_container.story.feedback_context.feedback_target_with_context.comet_ufi_summary_and_actions_renderer.feedback
            feedback = comet_sections["feedback"]["story"]["story_ufi_container"]["story"]["feedback_context"]["feedback_target_with_context"]["comet_ufi_summary_and_actions_renderer"]["feedback"]
            # $.raw_data[0].data.node.timeline_list_feed_units.edges[0].node.comet_sections.feedback.story.story_ufi_container.story.feedback_context.feedback_target_with_context.comet_ufi_summary_and_actions_renderer.feedback.reaction_count.count
            reaction_count = feedback["reaction_count"]["count"]
            share_count = feedback["share_count"]["count"]
            # $.raw_data[0].data.node.timeline_list_feed_units.edges[0].node.comet_sections.feedback.story.story_ufi_container.story.feedback_context.feedback_target_with_context.comet_ufi_summary_and_actions_renderer.feedback.comment_rendering_instance.comments.total_count
            comment_count = feedback["comment_rendering_instance"]["comments"]["total_count"]
            
            sub_reactions = self.process_reactions(feedback["top_reactions"])
            
            extracted_data.append({
                "post_id": post_id,
                "post_url": post_url,
                "profile_name": profile_name,
                "profile_short_name": profile_short_name,
                "profile_id": profile_id,
                "profile_url": profile_url,
                "permalink": permalink,
                "content": content,
                "hashtags": hashtags,
                "post_type": post_type,
                "number_of_media": number_of_media,
                "media_items": media_items,
                "creation_time": creation_time,
                "published_at": published_at,
                "published_date": published_date,
                "reaction_count": reaction_count,
                "share_count": share_count,
                "comment_count": comment_count,
                "sub_reactions": sub_reactions,
            })
        return extracted_data


    def requests_flow(
        self,
        doc_id: str,
        fb_userid: str,
        days_limit: int,
        display_progress=True,
    ):
        all_posts = []
        url = "https://www.facebook.com/api/graphql/"
        before_time = get_before_time()
        loop_limit = 5000
        next_cursor = None
        # Extract data
        for i in range(loop_limit):
            payload_in = get_payload(
                doc_id_in=doc_id,
                id_in=fb_userid,
                before_time=before_time,  # input before_time
                cursor=next_cursor,
            )        

            response = requests.post(
                url=url,
                data=payload_in,
                timeout=30,
            )
            body = response.content
            decoded_body = body.decode("utf-8")
            body_content = decoded_body.split("\n")
            next_cursor = get_next_cursor(body_content_in=body_content)
            # Not extract last line (it's always empty)
            extracted_data = self.extract_raw_data(body_content=body_content)
            all_posts.extend(extracted_data)
            # Check progress
            next_page_status = get_next_page_status(body_content=body_content)

            before_time = str(self.creation_list[-1])
            if not next_page_status:
                print("There are no more posts.")
                break

            # date_object = int(datetime.strptime(before_time, "%Y-%m-%d"))
            if compare_timestamp(
                timestamp=int(before_time),
                days_limit=days_limit,
                display_progress=display_progress,
            ):
                print(
                    f"The scraper has successfully retrieved posts from the past {str(days_limit)} days."
                )
                break
        
        # new_reactions = self.process_reactions(res_in=res_out)
        # # create result
        # final_res = self.format_data(
        #     res_in=res_out,
        #     fb_username_or_userid=fb_userid,
        #     new_reactions=new_reactions,
        # )
        return all_posts
