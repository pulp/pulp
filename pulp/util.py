
def get_param_as_list(key, data):
    '''
    Simple util to fetch a request variable and make sure we get a list back
    '''
    values = data.get(key)
    if not isinstance(values, list):
        values = [values]
    return values
 