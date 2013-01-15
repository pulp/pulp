# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt


ABRT_URL = 'http://repos.fedorapeople.org/repos/abrt/abrt/fedora-18/x86_64/'

ABRT_FILES = ['abrt-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-addon-ccpp-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-addon-kerneloops-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-addon-python-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-addon-vmcore-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-addon-xorg-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-cli-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-dbus-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-debuginfo-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-desktop-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-devel-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-gui-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-libs-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-plugin-bodhi-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-retrace-client-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'abrt-tui-2.0.19.121.g9526-1.fc18.x86_64.rpm',
              'btparser-0.24-1.fc18.x86_64.rpm',
              'btparser-debuginfo-0.24-1.fc18.x86_64.rpm',
              'btparser-devel-0.24-1.fc18.x86_64.rpm',
              'btparser-python-0.24-1.fc18.x86_64.rpm',
              'gnome-abrt-0.2.6-1.dirty.06672175400e22fed3cdb3ef82c61fccbf743807.fc18.x86_64.rpm',
              'gnome-abrt-debuginfo-0.2.6-1.dirty.06672175400e22fed3cdb3ef82c61fccbf743807.fc18.x86_64.rpm',
              'libreport-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-anaconda-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-cli-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-compat-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-debuginfo-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-devel-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-fedora-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-filesystem-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-gtk-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-gtk-devel-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-newt-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-plugin-bugzilla-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-plugin-kerneloops-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-plugin-logger-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-plugin-mailx-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-plugin-reportuploader-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-plugin-rhtsupport-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-plugin-ureport-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-python-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-web-2.0.20.19.gb4c7-1.fc18.x86_64.rpm',
              'libreport-web-devel-2.0.20.19.gb4c7-1.fc18.x86_64.rpm']


def abrt_file_urls():
    return [ABRT_URL + file_name for file_name in ABRT_FILES]


