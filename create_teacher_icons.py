from wand.image import Image
import os

for image in os.listdir("teacher_photos"):
    with Image(filename=('teacher_photos\\' + str(image))) as img:
        if (img.width > img.height):
            img.resize((96 * img.width) / img.height, 96)
            border = (img.width - 96) / 2
            img.crop(border, 0, width=96, height=96)
        else:
            img.resize(96, (96 * img.height) / img.width)
            border = (img.height - 96) / 2
            img.crop(0, border, width=96, height=96)
        img.convert('jpeg')
        
        img.save(filename='96x96_photos\\' + os.path.splitext(image)[0] + '.jpg')