import json
import argparse
from datetime import datetime

def convert_posts_to_zod_schema(input_json_path, output_json_path):
    with open(input_json_path, 'r', encoding='utf-8') as f:
        posts = json.load(f)

    file_list = []
    for post in posts:
        # If there is a media array, process each media item
        if "media" in post:
            for media_item in post["media"]:
                entry = {
                    "filepath": media_item.get("uri"),
                }
                metadata = {}
                if "title" in media_item and media_item["title"] not in (None, "null", ""):
                    metadata["_Caption"] = media_item["title"]

                    metadata["_blank_1"] = ""
                if "uri" in media_item:
                    metadata["_Filepath"] = media_item["uri"]
                    metadata["_blank_2"] = ""

                if "creation_timestamp" in media_item:
                    try:
                        ts = int(media_item["creation_timestamp"])
                        dt = datetime.fromtimestamp(ts)
                        metadata["_blank_3"] = ""

                        #metadata["_Created"] = dt.strftime("%b %d, %Y %H:%M")
                        metadata["_title"] = dt.strftime("%b %d, %Y %H:%M")

                        # add title to entry
                    except Exception:
                        #metadata["_Created"] = str(media_item["creation_timestamp"])
                        entry["_title"] = str(media_item["creation_timestamp"])

                if metadata:
                    entry["metadata"] = metadata

                file_list.append(entry)
        else:
            # Fallback for posts without media array
            entry = {
                "filepath": post.get("uri"),
            }
            # metadata = {}
            # if "title" in post:
            #     metadata["title"] = post["title"]
            # if metadata:
            #     entry["metadata"] = metadata
            # if "qr_data" in post:
            #     entry["qr_data"] = post["qr_data"]
            file_list.append(entry)

    with open(output_json_path, 'w', encoding='utf-8') as f:
        # for x in file_list:
        #     print("creation_timestamp is ", x.get("metadata", {}).get("_title", ""))
        # file_list.sort(
        #     key=lambda x: x.get("metadata", {}).get("_title", "")
        # )
        json.dump(file_list, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Convert Instagram posts JSON to Zod schema format.")
    parser.add_argument("--input-json", required=True, help="Path to input JSON file.")
    parser.add_argument("--output-json", required=True, help="Path to output JSON file.")
    args = parser.parse_args()

    convert_posts_to_zod_schema(args.input_json, args.output_json)

if __name__ == "__main__":
    main()