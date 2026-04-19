# -*- coding: utf-8 -*-
import json
from urllib.parse import parse_qs, unquote
from whatisfacebook.utils.utils import *


class RequestsParser(object):
    def __init__(self) -> None:
        self.en_reaction_names = [
            "like",
            "haha",
            "angry",
            "love",
            "care",
            "sorry",
            "wow",
        ]

    def _clean_res(self):
        self.res_new = []
        self.feedback_list = []
        self.context_list = []
        self.creation_list = []
        self.owning_profile = []
        self.raw_nodes = []  # Store full node data for enhanced extraction

    def parse_body(self, body_content):
        for each_body in body_content:
            json_data = json.loads(each_body)
            self.res_new.append(json_data)
            try:
                each_res = json_data["data"]["node"].copy()
                each_feedback = find_feedback_with_subscription_target_id(each_res)
                if each_feedback:
                    self.feedback_list.append(each_feedback)
                    message_text = find_message_text(json_data)
                    creation_time = find_creation(json_data)
                    owing_profile = find_owning_profile(json_data)
                    if message_text:
                        self.context_list.append(message_text)
                    elif not message_text:
                        self.context_list.append(None)
                    if creation_time:
                        self.creation_list.append(creation_time)
                    self.owning_profile.append(owing_profile)
                    # Store raw node data for enhanced field extraction
                    self.raw_nodes.append(each_res)

            # Did not display or record error message at here
            except Exception as e:
                print(f"PARSER ERROR: {e}")
                pass

    def collect_posts(self):
        res_out = []
        for each in self.feedback_list:
            res_out.append(
                {
                    "post_id": each["subscription_target_id"],
                    "reaction_count": each["reaction_count"],
                    "top_reactions": each["top_reactions"],
                    "share_count": each["share_count"],
                    "comment_rendering_instance": each["comment_rendering_instance"],
                    "video_view_count": each["video_view_count"],
                }
            )
        return res_out

    def process_reactions(self, reactions_in) -> dict:
        """Extract sub reaction value:
        Args:
            reactions_in (_type_): _description_
        Returns:
            _dict_: {
                "like": value,
                "haha": value,
                "angry": value,
                "love": value,
                "care": value,
                "sorry": value,
                "wow": value
        }
        Note:
        """
        reaction_hash = {}
        for each_react in reactions_in:
            reaction_hash[each_react["node"]["localized_name"]] = each_react[
                "reaction_count"
            ]  # get reaction value
        return reaction_hash
