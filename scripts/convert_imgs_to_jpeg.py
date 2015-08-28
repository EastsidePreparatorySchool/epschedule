from wand.image import Image
import os

for image in os.listdir("../teacher_photos"):
    with Image(filename=('../teacher_photos/' + str(image))) as img:
        img.save(filename='..\\teacher_photos_fullsize\\' + os.path.splitext(image)[0] + '.jpg')