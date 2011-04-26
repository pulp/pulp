#!/usr/bin/env python

import os
import shutil
import subprocess
import sys
import tempfile
from optparse import OptionParser



class GenRPMS(object):
    def __init__(self):
        self.parser = OptionParser()
        self.parser.add_option("--name", dest="name", action="store", help="Package name", default="pulp-test-package")
        self.parser.add_option("--start_ver", dest="start_ver", action="store", help="Start Version", default="1.0")
        self.parser.add_option("--arch", dest="arch", action="store", help="Package Arch", default="noarch")
        self.parser.add_option("--num", dest="num", action="store", help="Number of versions to create", default="1")
        self.opts = None
        self.args = None
        self.rpm_template = "rpm-template.spec"

    def parse(self):
        self.opts, self.args = self.parser.parse_args()
        self.version = float(self.opts.start_ver) #convert to float so it's easy to increment
        self.arch = self.opts.arch
        self.name = self.opts.name
        self.number = int(self.opts.num)

    def process(self):
        self.parse()
        for index in range(0, self.number):
            self.processRPM()

    def processRPM(self):
        temp_dir = tempfile.mkdtemp()
        try:
            temp_file_name = os.path.join(temp_dir, "%s.spec" % (self.name))
            shutil.copyfile(self.rpm_template, temp_file_name)
            subprocess.check_call(["sed", "-i", "s/REPLACE_NAME/%s/g" % (self.name), temp_file_name])
            subprocess.check_call(["sed", "-i", "s/REPLACE_ARCH/%s/g" % (self.arch), temp_file_name])
            subprocess.check_call(["sed", "-i", "s/REPLACE_VERSION/%s/g" % (self.version), temp_file_name])
            subprocess.check_call(["rpmbuild", "-ba", temp_file_name])
            self.version += 1.0
        finally:
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    gen_rpms = GenRPMS()
    gen_rpms.process()
