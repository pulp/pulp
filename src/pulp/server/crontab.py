#
# Copyright 2008, Martin Owens.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Rewritten from scratch, but based on the code from gnome-schedual by:
# - Philip Van Hoof <me at pvanhoof dot be>
# - Gaute Hope <eg at gaute dot vetsj dot com>
# - Kristof Vansant <de_lupus at pandora dot be>
#

"""
Example Use:

from crontab import CronTab

tab = CronTab()
cron = tab.new(command='/usr/bin/echo')

cron.minute().during(5,50).every(5)
cron.hour().every(4)

cron2 = tab.new(command='/foo/bar',comment='SomeID')
cron2.every_reboot()

list = tab.find_command('bar')
cron3 = list[0]
cron3.clear()
cron3.minute().every(1)

print unicode(tab.render())

for cron4 in tab.find_command('echo'):
    print cron4

for cron5 in tab:
    print cron5

tab.remove_all('echo')

t.write()
"""

import os, re, sys
import tempfile

__version__ = '0.9.3'

CRONCMD = "/usr/bin/crontab"
ITEMREX = re.compile('^\s*([^@#\s]+)\s+([^@#\s]+)\s+([^@#\s]+)' +
    '\s+([^@#\s]+)\s+([^@#\s]+)\s+([^#\n]*)(\s+#\s*([^\n]*)|$)')
SPECREX = re.compile('@(\w+)\s([^#\n]*)(\s+#\s*([^\n]*)|$)')
DEVNULL = ">/dev/null 2>&1"

MONTH_ENUM = [
    'jan', 'feb', 'mar', 'apr', 'may',
    'jun', 'jul', 'aug', 'sep', 'oct',
    'nov', 'dec',
]
WEEK_ENUM  = [
    'sun', 'mon', 'tue', 'wed', 'thu',
    'fri', 'sat', 'sun',
]

SPECIALS = {
    "reboot"  : '@reboot',
    "hourly"  : '0 * * * *',
    "daily"   : '0 0 * * *',
    "weekly"  : '0 0 * * 0',
    "monthly" : '0 0 1 * *',
    "yearly"  : '0 0 1 1 *',
    "annually": '0 0 1 1 *',
    "midnight": '0 0 * * *'
}

S_INFO = [
    { 'name' : 'Minutes',      'max_v' : 59, 'min_v' : 0 },
    { 'name' : 'Hours',        'max_v' : 23, 'min_v' : 0 },
    { 'name' : 'Day of Month', 'max_v' : 31, 'min_v' : 1 },
    { 'name' : 'Month',        'max_v' : 12, 'min_v' : 1, 'enum' : MONTH_ENUM },
    { 'name' : 'Day of Week',  'max_v' : 7,  'min_v' : 0, 'enum' : WEEK_ENUM },
]

class CronTab(object):
    """
    Crontab object which can access any time based cron using the standard.

    user = Set the user of the crontab (defaults to $USER)
    fake_tab = Don't set to crontab at all, set to testable fake tab variable.
    """
    def __init__(self, user=None, fake_tab=None):
        self.user  = user
        self.root  = ( os.getuid() == 0 )
        self.lines = None
        self.crons = None
        self.fake = fake_tab
        self.read()

    def read(self):
        """
        Read in the crontab from the system into the object, called
        automatically when listing or using the object. use for refresh.
        """
        self.crons = []
        self.lines = []
        if self.fake:
          lines = self.fake.split('\n')
        else:
          lines = os.popen(self._read_execute()).readlines()
        for line in lines:
            cron = CronItem(line)
            if cron.is_valid():
                self.crons.append(cron)
                self.lines.append(cron)
            else:
                self.lines.append(line.replace('\n',''))

    def write(self):
        """Write the crontab to the system. Saves all information."""
        # Add to either the crontab or the fake tab.
        if self.fake != None:
          self.fake = self.render()
          return

        filed, path = tempfile.mkstemp()
        fileh = os.fdopen(filed, 'w')
        fileh.write(self.render())
        fileh.close()
        # Add the entire crontab back to the user crontab
        os.system(self._write_execute(path))
        os.unlink(path)

    def render(self):
        """Render this crontab as it would be in the crontab."""
        crons = []
        for cron in self.lines:
            if type(cron) == CronItem and not cron.is_valid():
                crons.append("# " + unicode(cron))
                sys.stderr.write(
                    "Ignoring invalid crontab line `%s`\n" % str(cron))
                continue
            crons.append(unicode(cron))
        result = '\n'.join(crons)

        # jdobies, June 17, 2010: Added length check below from original code
        # to prevent an error when deleting the last cron entry in the file
        if len(result) == 0 or result[-1] not in [ '\n', '\r' ]:
            result += '\n'
        return result

    def new(self, command='', comment=''):
        """
        Create a new cron with a command and comment.

        Returns the new CronItem object.
        """
        item = CronItem(command=command, meta=comment)
        self.crons.append(item)
        self.lines.append(item)
        return item

    def find_command(self, command):
        """Return a list of crons using a command."""
        result = []
        for cron in self.crons:
            if cron.command.match(command):
                result.append(cron)
        return result

    def remove_all(self, command):
        """Removes all crons using the stated command."""
        l_value = self.find_command(command)
        for c_value in l_value:
            self.remove(c_value)

    def remove(self, item):
        """Remove a selected cron from the crontab."""
        self.crons.remove(item)
        self.lines.remove(item)

    def _read_execute(self):
        """Returns the command line for reading a crontab"""
        return "%s -l%s" % (CRONCMD, self._user_execute())

    def _write_execute(self, path):
        """Return the command line for writing a crontab"""
        return "%s %s%s" % (CRONCMD, path, self._user_execute())

    def _user_execute(self):
        """User command switches to append to the read and write commands."""
        if self.user:
            return ' -u %s' % str(self.user)
        return ''

    def __iter__(self):
        return self.crons.__iter__()

    def __unicode__(self):
        return self.render()


class CronItem(object):
    """
    An item which objectifies a single line of a crontab and
    May be considered to be a cron job object.
    """
    def __init__(self, line=None, command='', meta=''):
        self.command = CronCommand(unicode(command))
        self._meta   = meta
        self.valid   = False
        self.slices  = []
        self.special = False
        self.set_slices()
        if line:
            self.parse(line)

    def parse(self, line):
        """Parse a cron line string and save the info as the objects."""
        result = ITEMREX.findall(line)
        if result:
            o_value = result[0]
            self.command = CronCommand(o_value[5])
            self._meta   = o_value[7]
            self.set_slices( o_value )
            self.valid = True
        elif line.find('@') < line.find('#') or line.find('#')==-1:
            result = SPECREX.findall(line)
            if result and SPECIALS.has_key(result[0][0]):
                o_value = result[0]
                self.command = CronCommand(o_value[1])
                self._meta   = o_value[3]
                value = SPECIALS[o_value[0]]
                if value.find('@') != -1:
                    self.special = value
                else:
                    self.set_slices( value.split(' ') )
                self.valid = True

    def set_slices(self, o_value=None):
        """Set the values of this slice set"""
        self.slices = []
        for i_value in range(0, 5):
            if not o_value:
                o_value = [None, None, None, None, None]
            self.slices.append(
                CronSlice(value=o_value[i_value], **S_INFO[i_value]))

    def is_valid(self):
        """Return true if this slice set is valid"""
        return self.valid

    def render(self):
        """Render this set slice to a string"""
        time = ''
        if not self.special:
            slices = []
            for i in range(0, 5):
                slices.append(unicode(self.slices[i]))
            time = ' '.join(slices)
        if self.special or time in SPECIALS.values():
            if self.special:
                time = self.special
            else:
                time = "@%s" % SPECIALS.keys()[SPECIALS.values().index(time)]

        result = "%s %s" % (time, unicode(self.command))
        if self.meta():
            result += " # " + self.meta()
        return result


    def meta(self, value=None):
        """Return or set the meta value to replace the set values"""
        if value:
            self._meta = value
        return self._meta

    def every_reboot(self):
        """Set to every reboot instead of a time pattern"""
        self.special = '@reboot'

    def clear(self):
        """Clear the special and set values"""
        self.special = None
        for slice_v in self.slices:
            slice_v.clear()

    def minute(self):
        """Return the minute slice"""
        return self.slices[0]

    def hour(self):
        """Return the hour slice"""
        return self.slices[1]

    def dom(self):
        """Return the day-of-the month slice"""
        return self.slices[2]

    def month(self):
        """Return the month slice"""
        return self.slices[3]

    def dow(self):
        """Return the day of the week slice"""
        return self.slices[4]

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.render()


class CronSlice(object):
    """Cron slice object which shows a time pattern"""
    def __init__(self, name, min_v, max_v, enum=None, value=None):
        self.name  = name
        self.min   = min_v
        self.max   = max_v
        self.enum  = enum
        self.parts = []
        self.value(value)

    def value(self, value=None):
        """Return the value of the entire slice."""
        if value:
            self.parts = []
            for part in value.split(','):
                if part.find("/") > 0 or part.find("-") > 0 or part == '*':
                    self.parts.append( self.get_range( part ) )
                else:
                    if self.enum and part.lower() in self.enum:
                        part = self.enum.index(part.lower())
                    try:
                        self.parts.append( int(part) )
                    except:
                        raise ValueError(
                            'Unknown cron time part for %s: %s' % (
                            self.name, part))
        return self.render()

    def render(self):
        """Return the slice rendered as a crontab"""
        result = []
        for part in self.parts:
            result.append(unicode(part))
        if not result:
            return '*'
        return ','.join(result)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.render()

    def every(self, n_value):
        """Set the every X units value"""
        self.parts = [ self.get_range( '*/%d' % int(n_value) ) ]

    def on(self, *n_value):
        """Set the on the time value."""
        self.parts += n_value

    def during(self, value_from, value_to):
        """Set the During value, which sets a range"""
        range_value = self.get_range(
            "%s-%s" % (str(value_from), str(value_to)))
        self.parts.append( range_value )
        return range_value

    def clear(self):
        """clear the slice ready for new vaues"""
        self.parts = []

    def get_range(self, range_value):
        """Return a cron range for this slice"""
        return CronRange( self, range_value )


class CronRange(object):
    """A range between one value and another for a time range."""
    def __init__(self, slice_value, range_value=None):
        self.value_from = None
        self.value_to = None
        self.slice = slice_value
        self.seq   = 1
        if not range_value:
            range_value = '*'
        self.parse(range_value)

    def parse(self, value):
        """Parse a ranged value in a cronjob"""
        if value.find('/') > 0:
            value, self.seq = value.split('/')
        if value.find('-') > 0:
            from_val, to_val = value.split('-')
            self.value_from = self.clean_value(from_val)
            self.value_to  = self.clean_value(to_val)
        elif value == '*':
            self.value_from = self.slice.min
            self.value_to  = self.slice.max
        else:
            raise ValueError, 'Unknown cron range value %s' % value

    def render(self):
        """Render the ranged value for a cronjob"""
        value = '*'
        if self.value_from > self.slice.min or self.value_to < self.slice.max:
            value = "%d-%d" % (int(self.value_from), int(self.value_to))
        if int(self.seq) != 1:
            value += "/%d" % (int(self.seq))
        return value

    def clean_value(self, value):
        """Return a cleaned value of the ranged value"""
        if self.slice.enum and str(value).lower() in self.slice.enum:
            value = self.slice.enum.index(str(value).lower())
        try:
            value = int(value)
            if value >= self.slice.min and value <= self.slice.max:
                return value
        except ValueError:
            raise ValueError('Invalid range value %s' % str(value))

    def every(self, value):
        """Set the sequence value for this range."""
        self.seq = int(value)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.render()


class CronCommand(object):
    """Reprisent a cron command as an object."""
    def __init__(self, line):
        self._command = line

    def match(self, command):
        """Match the command given"""
        if command in self._command:
            return True
        return False

    def command(self):
        """Return the command line"""
        return self._command

    def __str__(self):
        """Return a string as a value"""
        return self.__unicode__()

    def __unicode__(self):
        """Return unicode command line value"""
        return self.command()

