from Crypto.Hash import SHA256
import os
import base64

def open_data_file(filename):
    return open(filename, 'rb')

def load_data_file(filename):
    return open_data_file(filename).read()

CRYPTO_KEY = load_data_file('../data/crypto.key').strip()

print CRYPTO_KEY

photos = os.listdir("../school_photos")

for filename in photos:
    hasher_input = filename[:-4]

    hasher = SHA256.new(CRYPTO_KEY)
    hasher.update(hasher_input)
    hashed = hasher.hexdigest()

    print hasher_input + " --> " + hashed

    os.rename("../school_photos/" + filename, "../school_photos/" + hashed + ".jpg")