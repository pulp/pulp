import os, os.path

path = "./definitions"
for name in os.listdir(path):
    fullpath = path + "/" + name
    #print "Working with ", fullpath
    if os.path.isfile(fullpath):
        print "Found file: ", fullpath

