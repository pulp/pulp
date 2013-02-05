Content Applicability
=====================

Determine Content Applicability
-------------------------------

Determines whether content units are applicable to the specified `consumers` using 
specified 'repositories'. What unit *applicability* means varies based on the
type of content unit. Consumers and repositories can be specified using criteria. 
Please see :ref:`search_api` for more details on how to specify the selection criteria for
consumers and repositories. Content units are specified in a dictionary keyed by content 
type ID string, value being a list of dictionaries of unit metadata used to identify 
content units to be checked for applicability. 

If repo_criteria is not specified, all the repositories bound to given consumers are considered 
when checking applicability. If consumer_criteria is not specified, but repo_criteria is specified, 
all the consumers registered to the Pulp server which are bound to specified repositories 
are checked for applicability. Units are also optional like consumer_criteria and repo_criteria. 
If they are not specified, all the units from specified repositories are checked for applicability. 
You can also specify content type ID with empty list as a value to check for all the units in 
given repositories with that content type. 

This api returns a dictionary keyed by consumer ID, further keyed by content type ID and a list 
of applicability reports as a value. 

Each *ApplicabilityReport* is an object:
 * **summary** (<dependent on plugin>) - summary of the applicability calculation
 * **details** (<dependent on plugin>) - details of the applicability calculation

| :method:`post`
| :path:`/v2/consumers/actions/content/applicability/`
| :permission:`read`
| :param_list:`post`

* :param:`consumer_criteria,object,a consumer criteria object defined in` :ref:`search_criteria`
* :param:`repo_criteria,object,a repository criteria object defined in` :ref:`search_criteria`
* :param:`units,dict,a dictionary of list of content unit metadata dictionaries to check, keyed by
          content type ID`

| :response_list:`_`

* :response_code:`200,if the applicability check was performed successfully`
* :response_code:`400,if one or more of the parameters is invalid`

| :return:`a dictionary keyed by consumer ID containing a list of applicability reports (see above),
           further keyed by content type ID`

:sample_request:`_` ::

{ 'consumer_criteria' : { 'filters': {'id': {'$in': ['sunflower', 'voyager']}},
                          'sort': [['id', 'ascending']]}

  'repo_criteria' : {'filters': {'id': {'$in': ['test-repo', 'unbound-repo', 'test_errata']}}}

  'units' : {'erratum': [{'id': 'RHBA-2007:0112'}],
 			 'rpm': [{'filename': 'pulp-test-package-0.3.1-1.fc11.x86_64.rpm'},
                     {'name': 'pulp-dot-2.0-test'}]}
}

:sample_response:`200` ::

 {u'sunflower': {u'erratum': [],
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
                           u'summary': {}}]},
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
