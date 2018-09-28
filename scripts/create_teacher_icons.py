from wand.image import Image
import os
import json

exceptions_file = open('photo_exceptions.json', 'rb')
exceptions = json.load(exceptions_file)

for image in os.listdir("../teacher_photos"):
    if ("_" not in image):
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

            x_except = 0
            y_except = 0
            for exception in exceptions:
                if str(image) == exception[0]:
                    x_except += exception[1]
                    y_except += exception[2]
            print "Calling: img.crop(" + str(cropparams[0] + x_except) + ", " + str(cropparams[1] + y_except) + ", " + str(img.width - cropparams[0] + x_except) + ", " + str(img.height - cropparams[1] + y_except) + ")"
            img.crop(cropparams[0] + x_except, cropparams[1] + y_except, img.width - cropparams[0] + x_except, img.height - cropparams[1] + y_except)
            img.type = 'grayscale'
            img.convert('jpeg')

            img.save(filename='../96x96_teachphotos/' + os.path.splitext(image)[0] + '.jpg')

    except Exception:
        print "No image found!"