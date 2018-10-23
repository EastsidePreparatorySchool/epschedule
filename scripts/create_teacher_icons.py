from wand.image import Image
import os
import json

exceptions_file = open('photo_exceptions.json', 'rb')
exceptions = json.load(exceptions_file)

for image in os.listdir("../teacher_photos"):
    if "_" not in image:
        continue
    print "Cropping " + str(image)
    try:
        with Image(filename=('../teacher_photos/' + str(image))) as img:
            if (img.width > img.height):
                img.resize((96 * img.width) / img.height, 96)
                border = (img.width - 96) / 2
                cropparams = [border, 0]
            else:
                img.resize(96, (96 * img.height) / img.width)
                border = (img.height - 96) / 2
                cropparams = [0, border]

            print "Calling: img.crop(" + str(cropparams[0]) + ", " + str(cropparams[1]) + ", " + str(img.width - cropparams[0]) + ", " + str(img.height - cropparams[1]) + ")"
            img.crop(cropparams[0], cropparams[1], img.width - cropparams[0], img.height - cropparams[1])
            img.type = 'grayscale'
            img.convert('jpeg')

            img.save(filename='../96x96_photos/' + os.path.splitext(image)[0] + '.jpg')

    except Exception:
        print "No image found!"