Orphaned Content
================
:term:`Content units` in Pulp are brought in as part of repository sync and
content upload operations. However, because content can be associated with more
than one repository, content is not removed when the repositories it is
associated with are removed or when the content is disassociated with
repositories.

Instead, if content is no longer associated with any repositories, it is
considered **orphaned**.

Orphaned content may be viewed and removed from Pulp using the following REST
calls.

Content types are defined by type definitions.


Viewing Orphaned Content
------------------------

Viewing all orphaned content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
List all orphaned content, regardless of type.

| :method:`get`
| :path:`/v2/content/orphans/`
| :permission:`read`
| :response_list:`_`

* :response_code:`200,even if no orphaned content is found`

| :return:`(possibly empty) list of content units`

:sample_response:`200` ::

 {
  [
  {u'_content_type_id': u'rpm',
   u'_href': u'/pulp/api/v2/content/orphans/rpm/d0dc2044-1edc-4298-bf10-a472ea943fe1/',
   u'_id': u'd0dc2044-1edc-4298-bf10-a472ea943fe1',
   u'_ns': u'units_rpm',
   u'_storage_path': u'/var/lib/pulp/content/rpm/.//gwt/2.3.0/1.fc16/noarch/c55f30d742a5dade6380a499df9fbf5e6bf35a316acf3774b261592cc8e547d5/gwt-2.3.0-1.fc16.noarch.rpm',
   u'arch': u'noarch',
   u'buildhost': u'localhost',
   u'checksum': u'c55f30d742a5dade6380a499df9fbf5e6bf35a316acf3774b261592cc8e547d5',
   u'checksumtype': u'sha256',
   u'description': u'Writing web apps today is a tedious and error-prone process.  Developers can\nspend 90% of their time working around browser quirks. In addition, building,\nreusing, and maintaining large JavaScript code bases and AJAX components can be\ndifficult and fragile. Google Web Toolkit (GWT) eases this burden by allowing\ndevelopers to quickly build and maintain complex yet highly performant\nJavaScript front-end applications in the Java programming language.',
   u'epoch': u'0',
   u'filename': u'gwt-2.3.0-1.fc16.noarch.rpm',
   u'license': u'ASL 2.0',
   u'name': u'gwt',
   u'relativepath': u'gwt-2.3.0-1.fc16.noarch.rpm',
   u'release': u'1.fc16',
   u'vendor': u'',
   u'version': u'2.3.0'},
  {u'_content_type_id': u'rpm',
   u'_href': u'/pulp/api/v2/content/orphans/rpm/5b8982b3-1d57-4822-92e5-effa0d4f0a17/',
   u'_id': u'5b8982b3-1d57-4822-92e5-effa0d4f0a17',
   u'_ns': u'units_rpm',
   u'_storage_path': u'/var/lib/pulp/content/rpm/.//gwt-javadoc/2.3.0/1.fc16/noarch/00da925d1a828f7e3985683ff68043523fe42ec3f1030f449cfddcc5854f6de1/gwt-javadoc-2.3.0-1.fc16.noarch.rpm',
   u'arch': u'noarch',
   u'buildhost': u'localhost',
   u'checksum': u'00da925d1a828f7e3985683ff68043523fe42ec3f1030f449cfddcc5854f6de1',
   u'checksumtype': u'sha256',
   u'description': u'Javadoc for gwt.',
   u'epoch': u'0',
   u'filename': u'gwt-javadoc-2.3.0-1.fc16.noarch.rpm',
   u'license': u'ASL 2.0',
   u'name': u'gwt-javadoc',
   u'relativepath': u'gwt-javadoc-2.3.0-1.fc16.noarch.rpm',
   u'release': u'1.fc16',
   u'vendor': u'',
   u'version': u'2.3.0'},
  {u'_content_type_id': u'rpm',
   u'_href': u'/pulp/api/v2/content/orphans/rpm/228762de-9762-4384-b41a-4ccc594467f9/',
   u'_id': u'228762de-9762-4384-b41a-4ccc594467f9',
   u'_ns': u'units_rpm',
   u'_storage_path': u'/var/lib/pulp/content/rpm/.//autotest/0.13.0/6.fc16/noarch/1c0009934068204b3937e49966b987ae925924b0922656640f39bcd0e85d52cd/autotest-0.13.0-6.fc16.noarch.rpm',
   u'arch': u'noarch',
   u'buildhost': u'localhost',
   u'checksum': u'1c0009934068204b3937e49966b987ae925924b0922656640f39bcd0e85d52cd',
   u'checksumtype': u'sha256',
   u'description': u"Autotest is a framework for fully automated testing. It is designed primarily\nto test the Linux kernel, though it is useful for many other functions such as\nqualifying new hardware. It's an open-source project under the GPL and is used\nand developed by a number of organizations, including Google, IBM, and many\nothers.\n\nThe autotest package provides the client harness capable of running autotest\njobs on a single system.",
   u'epoch': u'0',
   u'filename': u'autotest-0.13.0-6.fc16.noarch.rpm',
   u'license': u'GPLv2 and BSD and LGPLv2.1+',
   u'name': u'autotest',
   u'relativepath': u'autotest-0.13.0-6.fc16.noarch.rpm',
   u'release': u'6.fc16',
   u'vendor': u'',
   u'version': u'0.13.0'},
  ]
 }

The individual fields of the content units returned will vary by type. The above
sample is provided as a demonstration only and does not necessarily reflect the
exact return types of all calls. However all fields beginning with a **_** will
be available in all content units, regardless of type.

Viewing orphaned content by type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
List all the orphaned content of a particular content type.

| :method:`get`
| :path:`/v2/content/orphans/<content_type_id>/`
| :permission:`read`
| :response_list:`_`

* :response_code:`200,even if no orphaned content is found`
* :response_code:`404,if the content type does not exist`

| :return:`(possibly empty) list of content units`

View an individual orphaned content unit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Retrieve an individual orphaned content unit by content type and content id.

| :method:`get`
| :path:`/v2/content/orphans/<content_type_id>/<content_unit_id>/`
| :permission:`read`
| :response_list:`_`

* :response_code:`200,if the orphaned content unit is found`
* :response_code:`404,if the orphaned content unit does not exist`

| :return:`content unit`


Removing Orphaned Content
-------------------------
Removing orphans may entail deleting contents from disk and, as such, may
possibly be long-running process, so all these calls run asynchronously and
return a :ref:`call_report`

Removing all orphaned content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Remove all orphaned content units, regardless of type.

| :method:`delete`
| :path:`/v2/content/orphans/`
| :permission:`delete`
| :response_list:`_`

* :response_code:`202,even if no content is to be deleted`

| :return:`call report representing the current state of the delete`

Removing orphaned content by type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Remove all the orphaned content of a particular content type.

| :method:`delete`
| :path:`/v2/content/orphans/<content_type_id>/`
| :permission:`delete`
| :response_list:`_`

* :response_code:`202,even if no content is to be deleted`

| :return:`call report representing the current state of the delete`

Removing an individual orphaned content unit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Remove and individual orphaned content unit by content type and content id.

| :method:`delete`
| :path:`/v2/content/orphans/<content_type_id>/<content_unit_id>/`
| :permission:`delete`
| :response_list:`_`

* :response_code:`202,if the content unit is to be deleted`
* :response_code:`404,if the content does not exist`

| :return:`call report representing the current state of the delete`

Removing orphaned content units by type and id
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Individual content units across types may be deleted by this call. The body of
the call consists of a list of JSON objects with the fields:

* content_type: also known as the content_type_id
* content_id: also known as the content_unit_id

| :method:`post`
| :path:`/v2/content/actions/delete_orphans/`
| :permission:`delete`
| :param_list:`post`

* :param:`,array,JSON object containing the content_type and content_id fields`

| :response_list:`_`

* :response_code:`202,even if not content is to be deleted`

| :return:`call report representing the current state of the delete`
