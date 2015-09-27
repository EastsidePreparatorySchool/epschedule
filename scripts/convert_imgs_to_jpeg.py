from wand.image import Image
import os
import json

exceptions_file = open('photo_exceptions.json', 'rb')
exceptions = json.load(exceptions_file)
print exceptions

def get_shift(name, axis):
    for exception in exceptions:
        if exception[0][:-4] == name[:-4]:
            if axis == "x":
                return exception[1]
            elif axis == "y":
                return exception[2]
    return 0

def apply_exception(name, number, axis, axisvalue): # Takes in the name, current left or top value, "x" or "y", and the length of the x or y of the image
    shift = get_shift(name, axis)

    shift = (shift * axisvalue) / 96
    shift = int(round(shift)) # Round shift to the nearest int
    number += shift

    return number



for image in os.listdir("../teacher_photos"):
    with Image(filename=('../teacher_photos/' + str(image))) as img:
        if img.width > img.height:
            left = (img.width - img.height) / 2
            left = apply_exception(str(image), left, "x", img.width)
            img.crop(left, 0, width=img.height, height=img.height)
        elif img.width < img.height:
            top = (img.height - img.width) / 2
            top = apply_exception(str(image), top, "y", img.height)
            img.crop(0, top, width=img.width, height=img.width)
        img.save(filename='../teacher_photos_fullsize/' + os.path.splitext(image)[0] + '.jpg')