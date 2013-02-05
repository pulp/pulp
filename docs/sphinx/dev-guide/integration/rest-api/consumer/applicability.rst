Content Applicability
=====================

Determine Content Applicability
-------------------------------

Determines whether given content units are applicable to the specified `consumers` using 
specified `repositories`. What unit *applicability* means varies based on the
type of content unit. Consumers and repositories can be specified using criteria. 
Please see :ref:`search_api` for more details on how to specify the selection criteria for
consumers and repositories. Content units can be specified in a dictionary keyed by a content 
type ID, value being a list of dictionaries representing unit metadata used to identify 
content units to be checked for applicability. 

If repo_criteria is not specified, all the repositories bound to given consumers are considered. 
If consumer_criteria is not specified but repo_criteria is specified, all the consumers registered 
to the Pulp server which are bound to the specified repositories are checked for applicability. 
Units are also optional like consumer_criteria and repo_criteria. If they are not specified, 
all the units from specified repositories are checked for applicability. You can also specify 
content type ID with an empty list as a value to check for all the units in given repositories 
with that content type. 

This api returns a dictionary a dictionary containing a list of applicability reports keyed by a consumer ID, 
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
* :param:`units,dict,a dictionary of list of content unit metadata dictionaries to check, keyed by a content type ID`

| :response_list:`_`

* :response_code:`200,if the applicability check was performed successfully`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:`a dictionary containing a list of applicability reports(see above) keyed by a consumer ID, 
           further keyed by a content type ID`

:sample_request:`_` ::


{ 'consumer_criteria' : { 'filters': {'id': {'$in': ['sunflower', 'voyager']}},
                          'sort': [['id', 'ascending']]}

  'repo_criteria' : {'filters': {'id': {'$in': ['test-repo', 'unbound-repo', 'test_errata']}}}

  'units' : {'erratum': [{'id': 'grinder_test_4'}],
 			 'rpm': []}
}

:sample_response:`200` ::


{ u'sunflower': {u'erratum': [{u'details': {u'applicable_rpms': [{u'type_id': u'rpm',
                                                                  u'unit_key': {u'name': u'grinder_test_package.noarch'}}],
                                            u'upgrade_details': {u'grinder_test_package noarch': {u'available': {u'arch': u'noarch',
                                                                                                                 u'epoch': u'0',
                                                                                                                 u'filename': u'grinder_test_package-4.0-1.fc14.noarch.rpm',
                                                                                                                 u'name': u'grinder_test_package',
                                                                                                                 u'release': u'1.fc14',
                                                                                                                 u'src': u'grinder_test_package-4.0-1.fc14.src.rpm',
                                                                                                                 u'sum': [u'md5',
                                                                                                                          u'd89e83ed183fa55dfb0bd2eec14db93c'],
                                                                                                                 u'version': u'4.0'},
                                                                                                  u'installed': {u'arch': u'noarch',
                                                                                                                 u'epoch': 0,
                                                                                                                 u'name': u'grinder_test_package',
                                                                                                                 u'release': u'1.fc14',
                                                                                                                 u'vendor': None,
                                                                                                                 u'version': u'3.0'}}}},
                               u'summary': {}}],

                 u'rpm': [{u'details': {u'pulp-test-package x86_64': {u'available': {u'arch': u'x86_64',
                                                                                     u'checksum': u'6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f',
                                                                                     u'checksumtype': u'sha256',
                                                                                     u'epoch': u'0',
                                                                                     u'name': u'pulp-test-package',
                                                                                     u'release': u'1.fc11',
                                                                                     u'version': u'0.3.1'},
                                                                      u'installed': {u'arch': u'x86_64',
                                                                                     u'epoch': 0,
                                                                                     u'name': u'pulp-test-package',
                                                                                     u'release': u'1.fc11',
                                                                                     u'vendor': None,
                                                                                     u'version': u'0.2.1'}}},
                           u'summary': {}},
                 		  {u'details': {u'grinder_test_package noarch': {u'available': {u'arch': u'noarch',
                                                                                        u'checksum': u'78b6e9827dd3f3f02dd1ad16e89a3515a5b1e5ecdf522842a64315e3728aa951',
                                                                                        u'checksumtype': u'sha256',
                                                                                        u'epoch': u'0',
                                                                                        u'name': u'grinder_test_package',
                                                                                        u'release': u'1.fc14',
                                                                                        u'version': u'5.0'},
                                                                         u'installed': {u'arch': u'noarch',
                                                                                        u'epoch': 0,
                                                                                        u'name': u'grinder_test_package',
                                                                                        u'release': u'1.fc14',
                                                                                        u'vendor': None,
                                                                                        u'version': u'3.0'}}}]},
  u'voyager': {u'erratum': [],
               u'rpm': [{u'details': {u'pulp-test-package x86_64': {u'available': {u'arch': u'x86_64',
                                                                                   u'checksum': u'6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f',
                                                                                   u'checksumtype': u'sha256',
                                                                                   u'epoch': u'0',
                                                                                   u'name': u'pulp-test-package',
                                                                                   u'release': u'1.fc11',
                                                                                   u'version': u'0.3.1'},
                                                                    u'installed': {u'arch': u'x86_64',
                                                                                   u'epoch': 0,
                                                                                   u'name': u'pulp-test-package',
                                                                                   u'release': u'1.fc11',
                                                                                   u'vendor': None,
                                                                                   u'version': u'0.2.1'}}},
                         u'summary': {}}]}})
}
