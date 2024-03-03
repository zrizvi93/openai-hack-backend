import os
import requests

def save_image(image, prompt):
    image_dir = os.path.join(os.curdir, "images")
    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)
    file_name = f"{hash(prompt)}.png"
    generated_image_filepath = os.path.join(image_dir, file_name)
    generated_image_url = image.data[0].url
    generated_image = requests.get(generated_image_url).content
    with open(generated_image_filepath, "wb") as image_file:
        image_file.write(generated_image)
    return generated_image_url