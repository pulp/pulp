Content Applicability
=====================

Determine Content Applicability
-------------------------------

Determines whether given content units are applicable to the specified `consumers` using 
specified `repositories`. What unit *applicability* means varies based on the
type of content unit. Consumers and repositories can be specified using selection criteria. 
Please see :ref:`search_api` for more details on how to specify the selection criteria for
consumers and repositories. Content units to be checked for applicability can be specified 
in a dictionary keyed by a content type ID, value being a list of dictionaries representing 
unit metadata used to identify the content units. 

If repo_criteria is not specified, all the repositories bound to given consumers are considered. 
If consumer_criteria is not specified and repo_criteria is specified, all the consumers registered 
to the Pulp server which are bound to the specified repositories are checked for applicability. 
Units are also optional similar to consumer_criteria and repo_criteria. If they are not specified, 
all units from specified repositories are checked for applicability. You can also specify 
content type ID with an empty list as a value. In this case, the api will check for all units 
in given repositories with that content type. 

This api returns a dictionary containing a list of applicability reports keyed by a consumer ID, 
further keyed by a content type ID.

Each *ApplicabilityReport* is an object:
 * **summary** (<dependent on plugin>) - summary of the applicability calculation
 * **details** (<dependent on plugin>) - details of the applicability calculation

| :method:`post`
| :path:`/v2/consumers/actions/content/applicability/`
| :permission:`read`
| :param_list:`post`

* :param:`consumer_criteria,object,a consumer criteria object defined in` :ref:`search_criteria`
* :param:`repo_criteria,object,a repository criteria object defined in` :ref:`search_criteria`
* :param:`units,dict,a dictionary of list of content unit metadata dictionaries, keyed by a content type ID`

| :response_list:`_`

* :response_code:`200,if the applicability check was performed successfully`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:`a dictionary containing a list of applicability reports (see above) keyed by a consumer ID, 
           further keyed by a content type ID`

:sample_request:`_` ::


 { 
  'consumer_criteria': {
   'filters': {'id': {'$in': ['sunflower', 'voyager']}},
   'sort': [['id', 'ascending']]
  },
  'repo_criteria': {
   'filters': {'id': {'$in': ['test-repo', 'unbound-repo', 'test_errata']}}
  },
  'units': {
   'erratum': [{'id': 'grinder_test_4'}],
   'rpm': []
  }
 }


:sample_response:`200` ::


 { 
  'sunflower': {
   'erratum': [
    {'details': 
     {'applicable_rpms': [{'type_id': 'rpm', 'unit_key': {'name': 'grinder_test_package.noarch'}}],
      'upgrade_details': 
       {'grinder_test_package noarch': {
        'available': {
         'arch': 'noarch',
         'epoch': '0',
         'filename': 'grinder_test_package-4.0-1.fc14.noarch.rpm',
         'name': 'grinder_test_package',
         'release': '1.fc14',
         'src': 'grinder_test_package-4.0-1.fc14.src.rpm',
         'sum': ['md5','d89e83ed183fa55dfb0bd2eec14db93c'],
         'version': '4.0'
        },
        'installed': {
         'arch': 'noarch',
         'epoch': 0,
         'name': 'grinder_test_package',
         'release': '1.fc14',
         'vendor': None,
         'version': '3.0'
        }
       }
      }
     },
     'summary': {}
    }
   ],
   'rpm': [
    {'details': {
      'pulp-test-package x86_64': {
       'available': {
        'arch': 'x86_64',
        'checksum': '6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f',
        'checksumtype': 'sha256',
        'epoch': '0',
        'name': 'pulp-test-package',
        'release': '1.fc11',
        'version': '0.3.1'
       },
       'installed': {
        'arch': 'x86_64',
        'epoch': 0,
        'name': 'pulp-test-package',
        'release': '1.fc11',
        'vendor': None,
        'version': '0.2.1'
       }
      }
     },
     'summary': {}
    },
    {'details': {
      'grinder_test_package noarch': {
       'available': {
        'arch': 'noarch',
		'checksum': '78b6e9827dd3f3f02dd1ad16e89a3515a5b1e5ecdf522842a64315e3728aa951',
        'checksumtype': 'sha256',
        'epoch': '0',
        'name': 'grinder_test_package',
        'release': '1.fc14',
        'version': '5.0'
       },
       'installed': {
        'arch': 'noarch',
        'epoch': 0,
        'name': 'grinder_test_package',
        'release': '1.fc14',
        'vendor': None,
        'version': '3.0'
       }
      }
     }
    }
   ]
  },
  'voyager': {
   'erratum': [],
   'rpm': [
    {'details': {
      'pulp-test-package x86_64': {
       'available': {
        'arch': 'x86_64',
        'checksum': '6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f',
        'checksumtype': 'sha256',
        'epoch': '0',
        'name': 'pulp-test-package',
        'release': '1.fc11',
        'version': '0.3.1'
       },
       'installed': {
        'arch': 'x86_64',
        'epoch': 0,
        'name': 'pulp-test-package',
        'release': '1.fc11',
        'vendor': None,
        'version': '0.2.1'
       }
      }
     },
     'summary': {}
    }
   ]
  }
 }


