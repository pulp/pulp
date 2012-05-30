Package Manipulation
====================

.. _copy-packages:

Copy Packages Between Repositories
----------------------------------

Pulp supports the ability to copy packages between repositories. The entire
contents of a repository can be copied or criteria can be specified to select
only a subset of packages. This criteria can revolve around the package metadata,
information about when it was associated to the source repository, or both.

Only the association between the repository and the package is copied. The
package is stored on disk only once and is not duplicated as part of this process.

The criteria used to determine which packages to copy falls under two categories:
package metadata and association metadata. Package metadata refers to fields on
the RPM itself, for example name, version, arch, or description. Association
metadata refers to the time and manner in which it was added to the source
repository, for example the time it was first added to the repository or if
it was added during a sync or manually by a user.

There is a separate command for each type of unit in a repository to be copied
(e.g. rpm v. errata). All of the commands can be found in the ``repo copy``
section of the CLI.

All commands under the copy section require the following arguments:

``--from-repo-id, -f``
  Source repository from which packages will be copied.

``--to-repo-id, -t``
  Destination repository into which packages will be copied. A repository with
  the given ID must already exist before this call.

``--dry-run, -d``
  If specified, a list of the packages that match the given criteria will be
  displayed but the copy is not performed. This argument is meant to provide a way
  to verify the packages before committing the change to the server.

The following arguments can be passed to the package related (RPM, SRPM, DRPM)
copy commands. They are divided by the metadata type being matched.

Unit
^^^^

All of the values to the following argument indicate a field in the package's
metadata and the value to match against. The value can be a literal or a
regular expression. For example, to match on a package named "pulp"::

 --match "name=pulp"

An example of matching all packages that start with "p"::

 --match "name=^p.*"

Both arguments and field names may be repeated for more advanced criteria::

 --match "name=pulp.*" --match "name=.*okaara.*" --gte "version=2"

Pulp uses PCRE (Perl-compatible regular expressions) as the regular expression
dialect. More information can be found at `<http://www.pcre.org/pcre.txt>`_.

Valid fields are: name, epoch, version, release, arch,
buildhost, checksum, description, filename, license, and vendor.

``--match``
  Selects packages whose value for the given field matches the specified value.
  Example of selecting only i386 and x86_64 packages: ``--match "arch=i386" --match "arch=x86_64"``

``-not``
  Selects packages whose value for the given field does *not* match the specified
  value. Example of selecting all non-pulp packages in a repository: ``--not "name=^pulp.*"``

``--gt``
  Selects packages whose value for the given field is greater than (but not equal
  to) the specified value. Example of selecting all packages beyond version 1.0: ``--gt "version=1.0"``

``--gte``
  Selects packages whose value for the given field is greater than or equal to
  the specified value. Example of selecting all releases in a 2.x stream: ``--gte "version=2"``

``--lt``
  Selects packages whose value for the given field is less than (but not equal to)
  the specified value.

``--lte``
  Selects packages whose value for the given field is less than or equal to the
  specified value.

Association
^^^^^^^^^^^

The time when the package was first added to the source repository is a
valid criteria option. The following two arguments accept an :term:`iso8601`
timestamp as the value. For example, to copy packages added after May 1st, 2012::

 --after 2012-05-01

``--after``
  Selects packages first added to the source repository on or after the specified
  time.

``--before``
  Selects packages first added to the source repository on or before the specified
  time.

.. _upload-packages:

Uploading Packages Into a Repository
------------------------------------

RPMs may be uploaded into any Pulp repository. The client keeps track of in
progress uploads which may be paused and resumed at any time. The client will
remain active while uploading, however multiple instances of the client may be
run to perform multiple concurrent uploads.

The server database is updated to reflect the new packages in the repository,
however the uploaded RPMs are not immediately present in the published repository.
The are not made public until the next publish operation runs. More information
on this process can be found in the :ref:`repository publish <repo-publish>`
section of the user guide.

RPMs may be specified individually or by providing a directory; the client will
locate all RPMs in the directory and queue them for upload. These two options
may be used in conjunction with each other and multiples of either (individual
files or directories) are supported. The client will assemble the total list of
RPMs prior to beginning the upload process.

The client performs the following steps for each RPM to upload:

* Extract the relevant metadata about the file itself and from the RPM headers.
* Create a new upload request on the server.
* Save tracking information on the upload request and RPM to be uploaded on the
  client itself, allowing the client to resume in progress downloads if interrupted.
* Begin the upload process. The client will keep track of how much of the file
  has been uploaded, allowing the client to resume the upload at a later point.
* Request the server import the uploaded unit into the repository.
* If the import is successful, the upload request is deleted.

.. warning::
  If the destination repository is busy at the time the import is requested
  (for example, it is synchronizing), the import portion of the upload will be
  postponsed until the repository is available. If this happens, the client-side
  upload request is not deleted as described above. The repository tasks commands
  should be used to track the import task. Upon completion, the client-side
  upload request should be deleted using the :ref:`cancel command <upload-cancel>`.

.. warning::
  Much of the tracking information on the progress of an upload is stored
  client-side. As such, any upload request must be resumed/cancelled from the
  same client that initiated it. More specifically, if the client working directory
  (see :ref:`upload configuration values <upload-configuration>`) is in a
  user's home directory, only that user will have access to the necessary tracking
  files. However, the client can be run in multiple different processes to
  manipulate the same set of upload requests concurrently.

All upload related commands are found under the ``repo uploads`` section of
the client.

.. _upload-create:

Uploading One or More Packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``rpm`` command is used to initialize and upload packages into a repository.
After determining the list of RPMs to upload and initializing each upload
request in the server, each upload is then its own, independent request. If the
client is closed once the uploading begins, each RPM may be individually resumed
or cancelled at a later point. For convenience, this call will begin to
serially upload each requested file and import it into the repository.

The following arguments are available on the ``rpm`` command:

``--repo-id``
  Identifies the repository into which to upload the specified packages. This
  argument is required and must refer to an existing repository.

``--file, -f``
  Indicates a single RPM to upload. This argument may be specified multiple
  times to queue multiple upload calls in a single execution. This may also
  be used in conjunction with the ``--dir`` argument.

``--dir, -d``
  Refers to a directory in which one or more RPMs are located. Only files ending
  in ``.rpm`` will be retrieved from this directory and queued for upload. This
  may be specified multiple times to indicate multiple directories to search.

``-v``
  If specified, more detailed information about the upload will be displayed.

Below is the sample output from the ``rpm`` command when uploading two RPMs::

 $ pulp-admin repo uploads rpm --repo-id demo --file /rpms/medium-a-1-1.elfake.noarch.rpm --file /rpms/medium-b-1-1.elfake.noarch.rpm
 +----------------------------------------------------------------------+
                                RPM Upload
 +----------------------------------------------------------------------+

 Extracting necessary metdata for each RPM...
 [==================================================] 100%
 Analyzing: medium-b-1-1.elfake.noarch.rpm
 ... completed

 Creating upload requests on the server...
 [==================================================] 100%
 Initializing: medium-b-1-1.elfake.noarch.rpm
 ... completed

 Starting upload of selected packages. If this process is stopped through ctrl+c,
 the uploads will be paused and may be resumed later using the resume command or
 cancelled entirely using the cancel command.

 Uploading: medium-a-1-1.elfake.noarch.rpm
 [==================================================] 100%
 52435269/52435269 bytes
 ... completed

 Importing into the repository...
 ... completed

 Deleting the upload request...
 ... completed

 Uploading: medium-b-1-1.elfake.noarch.rpm
 [==================================================] 100%
 52435269/52435269 bytes
 ... completed

 Importing into the repository...
 ... completed

 Deleting the upload request...
 ... completed

Closing the client process by pressing ctrl+c during the upload step will
pause the upload for the in progress file. The uploads not yet started remain
in the "paused" state as well::

 Uploading: medium-a-1-1.elfake.noarch.rpm
 [====                                              ] 9%
 5242880/52435269 bytes
 ^CUploading paused

.. _upload-resume:

Resuming an In Progress Upload
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``resume`` command will allow one or more paused upload requests to resume
being uploaded to the server. The process remains the same following the upload
step; the request is imported and deleted.

The ``resume`` command displays a list of only paused uploads; uploads that are
currently running in another process will not be displayed. If multiple requests
are selected to resume, they will execute serially in the same fashion (along
with the same output) as the ``rpm`` command.

Below is an example of the menu to select paused uploads and the output once
the upload process has begun (output truncated once the upload process begins)::

 $ pulp-admin repo uploads resume
 +----------------------------------------------------------------------+
                             Upload Requests
 +----------------------------------------------------------------------+

 Select one or more uploads to resume:
   -  1 : medium-a-1-1.elfake.noarch.rpm
   -  2 : medium-c-1-1.elfake.noarch.rpm
   -  3 : medium-b-1-1.elfake.noarch.rpm
 Enter value (1-3) to toggle selection, 'c' to confirm selections, or '?' for
 more commands: 1

 Select one or more uploads to resume:
   x  1 : medium-a-1-1.elfake.noarch.rpm
   -  2 : medium-c-1-1.elfake.noarch.rpm
   -  3 : medium-b-1-1.elfake.noarch.rpm
 Enter value (1-3) to toggle selection, 'c' to confirm selections, or '?' for
 more commands: 2

 Select one or more uploads to resume:
   x  1 : medium-a-1-1.elfake.noarch.rpm
   x  2 : medium-c-1-1.elfake.noarch.rpm
   -  3 : medium-b-1-1.elfake.noarch.rpm
 Enter value (1-3) to toggle selection, 'c' to confirm selections, or '?' for
 more commands: c

 Resuming upload for: medium-a-1-1.elfake.noarch.rpm, medium-c-1-1.elfake.noarch.rpm

 Starting upload of selected packages. If this process is stopped through ctrl+c,
 the uploads will be paused and may be resumed later using the resume command or
 cancelled entirely using the cancel command.

 Uploading: medium-a-1-1.elfake.noarch.rpm
 [=================                                 ] 35%
 18874368/52435269 bytes


.. _upload-display:

Displaying Upload Requests
^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``list`` commands displays all upload requests known to the client. Each
entry will display the status of the upload and the name of the file being
uploaded.

Below is a sample output from the ``list`` command::

 $ pulp-admin repo uploads list
 +----------------------------------------------------------------------+
                             Upload Requests
 +----------------------------------------------------------------------+

 [ Running ] medium-a-1-1.elfake.noarch.rpm
 [ Paused  ] medium-c-1-1.elfake.noarch.rpm
 [ Paused  ] medium-b-1-1.elfake.noarch.rpm


.. _upload-cancel:

Cancelling an Upload Request
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Similar to :ref:`resuming paused uploads <upload-resume>`, the ``cancel`` command
displays a list of paused uploads to choose from. Running uploads, for instance
from another client process, are not eligable to be cancelled until they are
paused.

Cancel performs two steps:

* Inform the server the upload request is being removed.
* Deletes the client-side tracking files for the cancelled request.

In the event the server cannot be contacted or returns an error attempting
to delete the request (for instance, if the server was rebuilt and its knowledge
of the request was lost), the ``--force`` flag can be specified to the cancel
command. If this flag is present, the client-side tracking files will be
deleted regardless of whether or not a successful response is received from
the server.

Below is a sample output from the ``cancel`` command::

 $ pulp-admin repo uploads cancel
 +----------------------------------------------------------------------+
                             Upload Requests
 +----------------------------------------------------------------------+

 Select one or more uploads to cancel:
   -  1 : medium-a-1-1.elfake.noarch.rpm
   -  2 : medium-c-1-1.elfake.noarch.rpm
 Enter value (1-2) to toggle selection, 'c' to confirm selections, or '?' for
 more commands: 2

 Select one or more uploads to cancel:
   -  1 : medium-a-1-1.elfake.noarch.rpm
   x  2 : medium-c-1-1.elfake.noarch.rpm
 Enter value (1-2) to toggle selection, 'c' to confirm selections, or '?' for
 more commands: c

 Successfully deleted medium-c-1-1.elfake.noarch.rpm

.. _upload-configuration:

Configuration
^^^^^^^^^^^^^

The following configuration values in the client configuration apply to the
upload process.

``[filesystem] -> upload_working_dir``
  Local directory in which tracking files for each upload request are stored
  (defaults to ``~/.pulp/uploads``). These tracking files are small in size and
  should not represent a large space investment.

.. note::
  If the server is rebuilt while there are outstanding upload requests, the
  tracking files will remain on the client and should be manually deleted from
  this directory.

``[server] -> upload_chunk_size``
  A file is uploaded over the course of multiple calls to the server. This value,
  in bytes, is the maximum amount of data included in a single server upload
  call. The default is 1MB.

.. _orphaned-packages:

Orphaned Packages
-----------------

