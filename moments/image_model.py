import os
import requests
from dotenv import load_dotenv
import pathlib

load_dotenv()

API_KEY = os.getenv("AZURE_VISION_KEY")
ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT") + "/vision/v3.1/analyze?visualFeatures=Tags,Description,Categories"

def analyze_image(image_path):
    headers = {
        "Ocp-Apim-Subscription-Key": API_KEY,
        "Content-Type": "application/octet-stream"
    }
    image_path = pathlib.Path(image_path).resolve()
    with open(image_path, "rb") as image_data:
        response = requests.post(ENDPOINT, headers=headers, data=image_data)

    if response.status_code != 200:
        print(f"Error analyzing {image_path}: {response.status_code}, {response.text}")
        return "No description available.", ["No tags available."]

    result = response.json()
    print(f"API Response for {image_path}: {result}") 
    captions = result.get("description", {}).get("captions", [])
    caption = captions[0]["text"] if captions else "No description available."

    tags = []
    if "tags" in result:
        tags += [tag["name"] for tag in result["tags"]]
    if "description" in result and "tags" in result["description"]:
        tags += result["description"]["tags"]
    if "categories" in result:
        tags += [cat["name"] for cat in result["categories"]]

    return caption, list(set(tags)) if tags else ["No tags available."]


def process_existing_images(folder_path):
    from moments.core.extensions import db
    from moments.models import Photo, Tag

    images = [f for f in os.listdir(folder_path) if f.endswith((".jpg", ".png", ".jpeg"))]

    try:
        for image in images:
            image_path = os.path.join(folder_path, image)

            existing_photo = db.session.query(Photo).filter_by(filename=image).first()

            caption, generated_tags = analyze_image(image_path)

            if existing_photo:
                if not existing_photo.description or existing_photo.description.strip() == "":
                    existing_photo.description = caption
                else:
                    print(f"Keeping existing description for {image}")

                existing_photo.tags.clear()
            else:
                existing_photo = Photo(
                    filename=image,
                    filename_s=image,
                    filename_m=image,
                    author=None,
                    description=caption
                )
                db.session.add(existing_photo)

            for tag_name in generated_tags:
                tag = db.session.query(Tag).filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                    db.session.flush()

                if tag not in existing_photo.tags:
                    existing_photo.tags.append(tag)

            print(f"Processed {image}: Caption: {caption}, Tags: {generated_tags}")

        db.session.commit()
        print("Images uploaded successfully!")

    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
