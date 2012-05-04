Uploading Content
=================

Uploading a unit into a repository is a four step process:

* Create an upload request in Pulp. Pulp will provide an ID that is used for
  subsequent operations.
* Upload the bits for the new file. For large files, this can be done through
  multiple calls. This step is entirely optional; it is possible that a unit
  purely consists of metadata and possibly creating relationships to other
  units.
* Once the file is uploaded, metadata about the unit itself is provided to
  Pulp along with a destination repository. The repository's importer is
  contacted to perform the import which adds the unit to the database and
  associates it to the repository.
* Once the caller is finished importing the uploaded file, a request is sent
  to Pulp to delete the uploaded file from Pulp's temporary storage.

Uploaded files are not in the Pulp inventory until the import step. Units must
be imported into a repository that has an importer associated with it that is
capable of handling the unit type.

Creating an Upload Request
--------------------------

Informs Pulp of the desire to upload a new content unit. Pulp will perform any
preparation steps in the server and return an upload ID that is used to further
work with the upload request.

| :method:`post`
| :path:`/v2/content/uploads/`
| :permission:`create`
| :param_list:`post` None
| :response_list:`_`

* :response_code:`201,if the request to upload a file is granted`
* :response_code:`500,if the server cannot initialize the storage location for the file to be uploaded`

| :return:`upload ID to identify this upload request in future calls`

:sample_response:`201` ::

 {
  "_href": "/pulp/api/v2/content/uploads/cfb1fed0-752b-439e-aa68-fba68eababa3/",
  "upload_id': "cfb1fed0-752b-439e-aa68-fba68eababa3"
 }

Upload Bits
-----------

Sends a portion of the contents of the file being uploaded to the server. If the
entire file cannot be sent in a single call, the caller may divide up the file
and provide offset information for Pulp to use when assembling it.

| :method:`post`
| :path:`/v2/content/uploads/<upload_id>/<offset/`
| :permission:`update`
| :param_list:`post` The body of the request is the content to store in the file
  starting at the offset specified in the URL.
| :response_list:`_`

* :response_code:`200,if the content was successfully saved to the file`

| :return:`None`

Import into a Repository
------------------------

Provides metadata about the uploaded unit and requests Pulp import it into the
inventory and associate it with the given repository. This call is made on
the repository itself and the URL reflects this accordingly.

| :method:`post`
| :path:`/v2/repositories/<repo_id>/actions/import_upload/`
| :permission:`update`
| :param_list:`post`

* :param:`upload_id,str,identifies the upload request being imported`
* :param:`unit_type_id,str,identifies the type of unit the upload represents`
* :param:`unit_key,object,unique identifier for the new unit; the contents are contingent on the type of unit being uploaded`
* :param:`?unit_metadata,object,extra metadata describing the unit; the contents will vary based on the importer handling the import`

| :response_list:`_`

* :response_code:`200,if the import completed successfully`
* :response_code:`202,if the request for the import was accepted but postponed until later`

| :return:`None`

Delete an Upload Request
------------------------

Once the uploaded file has been successfully imported and no further operations
are desired, the caller should delete the upload request from the server.

| :method:`delete`
| :path:`/v2/content/uploads/<upload_id>`
| :permission:`delete`
| :param_list:`delete` None
| :response_list:`_`

* :response_code:`200,if the upload was successfully deleted`
* :response_code:`404,if the given upload ID is not found`

| :return:`None`

List All Upload Requests
------------------------

Returns a list of IDs for all upload requests currently in the server.

| :method:`get`
| :path:`/v2/content/uploads/`
| :permission:`read`
| :param_list:`get` None
| :response_list:`_`

* :response_code:`200,for a successful lookup`

| :return:`list of IDs for all upload requests on the server; empty list if there are none`

:sample_response:`200` ::

 {
  "upload_ids': ["cfb1fed0-752b-439e-aa68-fba68eababa3"]
 }
