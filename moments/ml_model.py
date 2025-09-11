import os
import requests
from dotenv import load_dotenv
import pathlib
# Load environment variables from .env file
load_dotenv()

# Retrieve API credentials
API_KEY = os.getenv("AZURE_VISION_KEY")
ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT") + "/vision/v3.1/analyze?visualFeatures=Tags,Description,Categories"

def generate_alt_text(image_path):
    headers = {
        "Ocp-Apim-Subscription-Key": API_KEY,
        "Content-Type": "application/octet-stream"
    }
    image_path = pathlib.Path(image_path).resolve()
    with open(image_path, "rb") as image_data:
        response = requests.post(ENDPOINT, headers=headers, data=image_data)

    if response.status_code == 200:
        result = response.json()

        tags = result.get("description", {}).get("tags", [])
        api_tags = [tag["name"] for tag in result.get("tags", [])]
        categories = [category["name"] for category in result.get("categories", [])] 

        final_tags = list(set(tags + api_tags + categories))

        print("Tags:", final_tags)

        return ", ".join(final_tags) if final_tags else "There are no tags."

    return "There are no tags."




def generate_tags(image_path):
    headers = {
        "Ocp-Apim-Subscription-Key": API_KEY,
        "Content-Type": "application/octet-stream"
    }

    with open(image_path, "rb") as image_data:
        response = requests.post(ENDPOINT, headers=headers, data=image_data)

    if response.status_code == 200:
        result = response.json()

        print(f"API Response for {image_path}: {result}")

        tags = []
        if "tags" in result:
            tags += [tag["name"] for tag in result["tags"]]
        if "description" in result and "tags" in result["description"]:
            tags += result["description"]["tags"]
        if "categories" in result:
            tags += [cat["name"] for cat in result["categories"]]

        return list(set(tags)) if tags else ["No tags available."]

    return ["There is no tags."]

def process_existing_images(folder_path):

    from moments.core.extensions import db
    from moments.models import Photo, Tag
    from flask import current_app

    images = [f for f in os.listdir(folder_path) if f.endswith((".jpg", ".png", ".jpeg"))]

    try:
        for image in images:
            image_path = os.path.join(folder_path, image)

            existing_photo = db.session.query(Photo).filter_by(filename=image).first()

            caption = generate_alt_text(image_path)

            generated_tags = generate_tags(image_path)

            if existing_photo:
                existing_photo.description = caption

                existing_photo.tags.clear()

                for tag_name in generated_tags:
                    tag = db.session.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                        db.session.flush()
                
                    if tag not in existing_photo.tags:
                        existing_photo.tags.append(tag)

                print(f"Updated {image}: Caption: {caption}, Tags: {generated_tags}")

            else:
                photo = Photo(
                    filename=image,
                    filename_s=image,
                    filename_m=image,
                    author=None,
                    description=caption
                )

                for tag_name in generated_tags:
                    tag = db.session.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                        db.session.flush()

                    photo.tags.append(tag)

                db.session.add(photo)
                print(f"Added new image {image} with Caption: {caption}, Tags: {generated_tags}")

        db.session.commit()
        print("Inages uploded successfully!")

    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")