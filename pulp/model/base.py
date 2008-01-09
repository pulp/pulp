# TODO:  We need to fix these methods to instead of using dicts to actually
# use real objects.  This requires fixing suds to be able to better support
# xml seralization of standard objects (vs just dicts and Property objects)

def get_page_control():
    pagecontrol = dict()
    pagecontrol['pageNumber'] = 0
    pagecontrol['pageSize'] = 100
    return pagecontrol

def get_new_channel(name, description):
    channel = dict()
    channel['name'] = name
    channel['description '] = description
    return channel

