import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import logging

logger = logging.getLogger("memerecommend")


class CloudinaryClient:
    def __init__(self):
        cloudinary.config(
            cloud_name="dfd5ywyyj",
            api_key="122416466455417",
            api_secret=os.getenv('CLOUDINARY_KEY')
        )

    def post_photo(self, path: str) -> str:
        """
        post photo and return its public url
        """
        try:
            resp = cloudinary.uploader.upload(path)
            return resp['url']
        except Exception as e:
            logger.exception('Error when loading photo to cloudinary' + e.__str__())
