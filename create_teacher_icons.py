from wand.image import Image
import os

exceptions = [["hayes.jpg", 20, 0], ["hollingshead.jpg", 20, 0], ["pedersen.jpg", -20, 0], ["sweet.jpg", 40, 0]]
for image in os.listdir("teacher_photos"):
    with Image(filename=('teacher_photos\\' + str(image))) as img:
        if (img.width > img.height):
            img.resize((96 * img.width) / img.height, 96)
            border = (img.width - 96) / 2
            cropparams = [border, 0]
        else:
            img.resize(96, (96 * img.height) / img.width)
            border = (img.height - 96) / 2
            cropparams = [0, border]
            
        for exception in exceptions:
            if str(image) == exception[0]:
                print "Exception excpetion"
                cropparams[0] += exception[1]
                cropparams[1] += exception[2]
                print cropparams
        img.crop(cropparams[0], cropparams[1], width=96, height=96)
        img.convert('jpeg')
        
        img.save(filename='96x96_photos\\' + os.path.splitext(image)[0] + '.jpg')