# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
    Property object used to provide an object wrapper around a complex dictionary.
    
    Eg::

        { 'name':{'first':'Elvis', 'middle':'Grant', 'last':'Prestley'},
           'age':30, 
           'address':{'address':'123 Lakepines Dr.','city':'Memphis', 'state':'TN', 'zip':'87373'},
           'phone':'919-555-1212',
           'records':[{'name':'Elvis', 'year':'1956'}, 
                          {'name':'Just for You', 'year':'1957'},
                          {'name':'GI Blues', 'year':'1960'}],
           'born':'1935',
           }
        p = Property(data)
        p.died = '1977'   # assign value
        hair = p.get(haircolor='black') # get value and specify a default.
        print p.age
        print 'name= %s, %s, %s' % (p.name.first, p.name.last, p.name.middle)
        print 'city=%s' % p.address.city
        print 'state=%s' % p.address.state
        print [r.name for r in p.records]
        print 'born %s died %s' % (p.born, p.died)
"""

class Property:
    
    __protected__ = ('__data__', '__strict__', '__type__', '__metadata__')
    
    """
    provides an object wrapper around a complex dictionary.
    """
    
    def __init__(self, data=None, strict=False):
        """
        data -- a dictionary containing properties.
        strict -- flag indicates whether __getattr__() will throw an exception
        when the name is not found
        """
        if data is None:
            data = {}
        if isinstance(data, Property):
            data = data.dict()
        self.__data__ = data
        self.__strict__ = strict
        self.__type__ = None
        self.__metadata__ = {}
            
    def get_names(self):
        """get a list of property names"""
        return self.__data__.keys()
        
    def get_values(self):
        """get a list of property values"""
        return self.__data__.values()

    def get_items(self):
        """ get the property's collection of items."""
        return self.__data__.items()
    
    def get(self, **kwargs):
        """get a property(s) value by name while specifying a default: property=default, """
        result = []
        for k in kwargs.keys():
            default = kwargs[k]
            value = self.__data__.get(k, default)
            result.append(self.translate(value))
        if len(result) == 1:
            return result[0]
        else:
            return tuple(result)
        
    def set(self, name, value):
        """set the value of the specified named"""
        self.__setattr__(name, value)
            
    def get_metadata(self, name):
        """ get the metadata associated with the named property"""
        if name in self.__metadata__:
            md = self.__metadata__[name]
        else:
            md = Property()
            self.__metadata__[name] = md
        return md       

    def dict(self):
        """get the underlying dictionary"""
        return self.__data__
    
    def prune(self):
        """prune the underlying dictionary of entries with value = none"""
        pruned = []
        for k in self.__data__.keys():
            v = self.__data__[k]
            if v is None:
                del self.__data__[k]
                pruned.append(k)
        return pruned
            
    def translate(self, v):
        """
        translate the specified value to ensure that dictionaries and collections
        of dictionaries are returned as a Propety or collection of properties
        """
        if isinstance(v, dict):
            return Property(v)
        if isinstance(v, tuple):
             return self.translate_tuple(v)
        if isinstance(v, list):
            return self.translate_list(v)
        return v
    
    def translate_list(self, collection):
        """
        translate the specified collection of dictionaries
        into a collection of Propety objects.
        """
        i = 0
        for item in collection:
            if isinstance(item, dict):
                collection[i] = Property(item)
            i += 1
        return collection
    
    def translate_tuple(self, collection):
        """
        translate the specified collection of dictionaries
        into a collection of Propety objects.
        """
        list = []
        for item in collection:
            if isinstance(item, dict):
                list.append(Property(item))
            else:
                list.append(item)
        return tuple(list)

    def __getattr__(self, name):
        """get the specified attribute (property).  raise exception based on strict flag"""
        result = None
        if name in Property.__protected__:
            return self.__dict__[name] 
        try:            
            result = self.translate(self.__data__[name])
        except KeyError:
            if self.__strict__:
                raise AttributeError, name
        return result
    
    def __setattr__(self, name, value):
        """set the value of the specified attribute (property)"""
        if name in Property.__protected__:
            self.__dict__[name] = value
            return
        if isinstance(value, Property):
            self.__data__[name] = value
            return
        if isinstance(value, list) or isinstance(value, tuple):
            _list = []
            for item in value:
                if isinstance(item, Property):
                    _list.append(item)
            self.__data__[name] = _list
            return
        self.__data__[name] = value

    def __getitem__(self, name):
        """ dictionary accessor """
        return self.translate(self.__data__[name])
        
    def __setitem__(self, name, value):
        """ dictionary accessor """
        self.__setattr__(name, value)
    
    def __str__(self):
        """ get a string representation """
        if self.__type__ is None:
            return prettyprint(self.__data__)
        else:
            return '(%s)%s' % (self.__type__, prettyprint(self.__data__))
    
    def __repr__(self):
        """ get a string representation """
        return self.__str__()
    
    def __neq__(self, other):
        """ not equals operator """
        return not self.__eq__(other)
    
    def __eq__(self, other):
        """ equals operator """
        if isinstance(other, Property):
            return self.__data__ == other.__data__
        else:
            return False
        
    def __len__(self):
        """ len() operator """
        return len(self.__data__)
    
    def __contains__(self, name):
        return name in self.__data__

    


from suds.prettyprint import PrettyPrinter
    
def prettyprint(object):
    return PrettyPrinter().tostring(object)
        