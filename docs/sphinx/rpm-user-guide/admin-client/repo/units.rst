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

Uploading Package Groups/Categories Into a Repository
-----------------------------------------------------

Package groups and categories may be uploaded into any Pulp repository.
Please refer to the RPM upload section for more details on the upload process.

.. _upload-create-package-group-or-category:

Uploading a Package Group
^^^^^^^^^^^^^^^^^^^^^^^^^

The ``group`` command is used to initialize and upload a package group into a repository.


The following arguments are available on the ``group`` command:

``--repo-id``
  Identifies the repository into which to upload the specified package group. This
  argument is required and must refer to an existing repository.

``--group-id, -i``
  The identifier for this package group.  This argument is required.

``--name, -n``
  Name of this package group.  This argument is required.

``--description, -d``
  Description of this package group.  This argument is required.

``--cond-name``
  Adds an entry to the conditional package name list under the package group.
  A conditional package entry will only install a package if the specified 
  required package name is installed on the system.  For example an entry 
  of 'foo-fr' may be marked as requiring 'foo'.  In this case if 'foo' is 
  installed on the system, then 'foo-fr' will be installed, otherwise 'foo-fr'
  is not installed.
  The format for this entry is: "package_name:required_package_name"
  Multiple entries may be indicated by specifying the argument multiple times.

``--mand-name``
  Adds an entry to the mandatory package name list under the package group.
  A mandatory package entry will always be installed if this package group is
  installed.  This means a GUI like Anaconda or PackageKit will not allow 
  deselecting this package for installation.
  Multiple entries may be indicated by specifying the argument multiple times.

``--opt-name``
  Adds an entry to the optional package name list under the package group.
  An optional package entry is typically not installed when this package group
  is installed, but it is possible if using something like PackageKit to select 
  this entry for installation.
  Multiple entries may be indicated by specifying the argument multiple times.

``--default-name, -p``
  Adds an entry to the default package name list under the package group.
  A default package entry is typically installed when the package group is
  installed, but it is possible if using something like PackageKit to unselect 
  a particular package.
  Multiple entries may be indicated by specifying the argument multiple times.

``--display-order``
  Sets the 'displayorder' value on the package group.  Typically an integer 
  suggesting when to display this package group.

``--langonly```
  Set the 'langonly' field on the package group.

``--default``
  If specified, this will set the "default" flag on the package group to True.
  If omitted the "default" flag is set to False

``--user-visible``
  If specified, this will set the "uservisible" flag on the package group to True.
  If omitted the "default" flag is set to False

``-v``
  If specified, more detailed information about the upload will be displayed.

Below is the sample output from the ``group`` command when uploading a package group::

 $ pulp-admin repo uploads group --repo-id demo --group-id devtools --name DevTools --description "List of development tools" -p scala -p sbt -p vim
 +----------------------------------------------------------------------+
                          Package Group Creation
 +----------------------------------------------------------------------+

 Starting upload of selected packages. If this process is stopped through ctrl+c,
 the uploads will be paused and may be resumed later using the resume command or
 cancelled entirely using the cancel command.
 
 Importing into the repository...
 ... completed

 Deleting the upload request...
 ... completed

Uploading a Package Category
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``category`` command is used to initialize and upload a package category into a repository.


The following arguments are available on the ``category`` command:

``--repo-id``
  Identifies the repository into which to upload the specified package category. This
  argument is required and must refer to an existing repository.

``--category-id, -i``
  The identifier for this package category.  This argument is required.

``--name, -n``
  Name of this package category.  This argument is required.

``--description, -d``
  Description of this package category.  This argument is required.

``--group, -g``
  Adds a package group id to this category.
  Multiple entries may be indicated by specifying the argument multiple times.

``--display-order``
  Sets the 'displayorder' value on the package category.  Typically an integer 
  suggesting when to display this package category.

``-v``
  If specified, more detailed information about the upload will be displayed.

Below is the sample output from the ``category`` command when uploading a package category::

  pulp-admin repo uploads category --repo-id demo --category-id apps --name Apps --description "Popular Applications" -g chrome -g xchat2 -g thunderbird 
  +----------------------------------------------------------------------+
                         Package Category Creation
  +----------------------------------------------------------------------+

  Starting upload of selected packages. If this process is stopped through ctrl+c,
  the uploads will be paused and may be resumed later using the resume command or
  cancelled entirely using the cancel command.

  Importing into the repository...
  ... completed

  Deleting the upload request...
  ... completed

Uploading an Erratum Into a Repository
--------------------------------------

An erratum may be uploaded into any Pulp repository.
Please refer to the RPM upload section for more details on the upload process.

.. _upload-create-erratum:

Uploading an Erratum
^^^^^^^^^^^^^^^^^^^^

The ``errata`` command is used to initialize and upload an erratum into a repository.


The following arguments are available on the ``erratum`` command:

``--repo-id``
  Identifies the repository into which to upload the specified erratum. This
  argument is required and must refer to an existing repository.

``--erratum-id, -i``
  The identifier for this erratum.  This argument is required.

``--title, -n``
  The title of this erratum.  This argument is required.

``--description, -d``
  Description of this erratum.  This argument is required.

``--version``
  The version of this erratum.  This argument is required.

``--release``           
  The release of this erratum.  This argument is required.

``--type, -t``
  The type of this erratum, common examples are: "bugzilla", "security", "enhancement".
  This argument is required.

``--status, -s``
  The status of this erratum, common example is "final".  This argument is required.

``--updated, -u``
  The date this erratum was updated.  The expected format is "YYYY-MM-DD HH:MM:SS".
  This argument is required.

``--issued``
  The date this erratum was issued.  The expected format is "YYYY-MM-DD HH:MM:SS".
  This argument is required.

``--reference-csv, -r``
  A path to a file containing reference information for this erratum.
  The format of the data in the file must be one line per record. 
  Each line must be in the format "href,type,id,title".
  Common examples of reference information would be bugzilla or CVE entries.

``--pkglist-csv, -p``
  A path to a file containing information on the packages associated to this erratum.
  The format of the data in the file must be one line per record.
  Each line must be in the format "name,version,release,epoch,arch,filename,checksum,checksum_type,sourceurl".
  This argument is required.

``--from``
  A string identifying who issued this erratum, typically an email address.
  This argument is required.

``--pushcount``
  Sets the 'pushcount' entry on this erratum, entry must be an integer.
  A default value of '1' will be used if not specified.

``--reboot-suggested``
  Sets the reboot suggested flag on the erratum if specified.

``--severity``
  Sets the severity of this erratum, expects a string.

``--rights``
  Sets the rights for this erratum, expects a string.

``--summary``
  Sets the summary for this erratum, expects a string.

``--solution``
  Sets the solution for this erratum, expects a string.

``-v``
  If specified, more detailed information about the upload will be displayed.

Below is a sample package list csv file::

  $ cat package_list.csv 
  xen,3.0.3,105.el5_5.2,0,i386,xen-3.0.3-105.el5_5.2.i386.rpm,0f1174b38383b01a77278b0d9f289987,md5,xen-3.0.3-105.el5_5.2.src.rpm
  xen-devel,3.0.3,105.el5_5.2,0,i386,xen-devel-3.0.3-105.el5_5.2.i386.rpm,3680d1dde276fd155ead7203508fed30,md5,xen-3.0.3-105.el5_5.2.src.rpm

Below is a sample references csv file::
  
  $ cat references.csv 
  http://bugzilla.redhat.com/bugzilla/show_bug.cgi?id=580398,bugzilla,580398,Windows Logo testing likes its PCI classes to be consistent
  http://bugzilla.redhat.com/bugzilla/show_bug.cgi?id=517903,bugzilla,517903,Add -no-kvm-pit-reinject in qemu cmdline for RHEL guests

Below is the sample output from the ``errata`` command when uploading an erratum::

  $ pulp-admin repo uploads errata --repo-id errata_demo --erratum-id DEMO_ID_1342457000 --title "Demo Errata created on Mon Jul 16 12:43:20 EDT 2012" --description "This is the description" --version 1 --release el6 --type enhancement --status final --updated "Mon Jul 16 12:43:20 EDT 2012" --issued "Mon Jul 16 12:43:20 EDT 2012" --reference-csv references.csv --pkglist-csv package_list.csv --from "pulp-list@redhat.com" --pushcount 1 --severity "example severity" --rights "example rights" --summary "example summary" --solution "solution text would go here"  -v
  +----------------------------------------------------------------------+
                               Erratum Creation
  +----------------------------------------------------------------------+

  Erratum Details:
    Id:                DEMO_ID_1342457000
    Title:             Demo Errata created on Mon Jul 16 12:43:20 EDT 2012
    Type:              enhancement
    Severity:          example severity
    Status:            final
    Solution:          solution text would go here
    Issued:            Mon Jul 16 12:43:20 EDT 2012
    Updated:           Mon Jul 16 12:43:20 EDT 2012
    From Str:          pulp-list@redhat.com
    Version:           1
    Release:           el6
    Description:       This is the description
    Summary:           example summary
    Pkglist:           
      Name:     el6
      Packages: 
        Arch:     i386
        Epoch:    0
        Filename: xen-3.0.3-105.el5_5.2.i386.rpm
        Name:     xen
        Release:  105.el5_5.2
        Src:      xen-3.0.3-105.el5_5.2.src.rpm
        Sums:     0f1174b38383b01a77278b0d9f289987
        Type:     md5
        Version:  3.0.3
        Arch:     i386
        Epoch:    0
        Filename: xen-devel-3.0.3-105.el5_5.2.i386.rpm
        Name:     xen-devel
        Release:  105.el5_5.2
        Src:      xen-3.0.3-105.el5_5.2.src.rpm
        Sums:     3680d1dde276fd155ead7203508fed30
        Type:     md5
        Version:  3.0.3
    Short:    
    Pushcount:         1
    Reboot Suggested:  False
    References:        
      Href:  http://bugzilla.redhat.com/bugzilla/show_bug.cgi?id=580398
      Id:    580398
      Title: Windows Logo testing likes its PCI classes to be consistent
      Type:  bugzilla
      Href:  http://bugzilla.redhat.com/bugzilla/show_bug.cgi?id=517903
      Id:    517903
      Title: Add -no-kvm-pit-reinject in qemu cmdline for RHEL guests
      Type:  bugzilla
    Rights:            example rights

  Starting upload of selected packages. If this process is stopped through ctrl+c,
  the uploads will be paused and may be resumed later using the resume command or
  cancelled entirely using the cancel command.

  Importing into the repository...
  ... completed

  Deleting the upload request...
  ... completed

Orphaned Packages
-----------------

