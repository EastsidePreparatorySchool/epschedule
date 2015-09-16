from wand.image import Image
import os

for image in os.listdir("../teacher_photos"):
    with Image(filename=('../teacher_photos/' + str(image))) as img:
    	if img.width > img.height:
    		left = (img.width - img.height) / 2
    		img.crop(left, 0, width=img.height, height=img.height)
       	elif img.width < img.height:
    		top = (img.height - img.width) / 2
    		img.crop(0, top, width=img.width, height=img.width)
        img.save(filename='..\\teacher_photos_fullsize\\' + os.path.splitext(image)[0] + '.jpg')