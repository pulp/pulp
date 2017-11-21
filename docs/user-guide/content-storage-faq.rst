Content Storage FAQ
===================

**How Pulp determines uniqueness when storing units?**

Uniqueness of each content type is determined by it's unit key. A unit key is
a combination of content attributes. The following combinations of attributes
represents the unit key for some of the content type supported by Pulp.

**DRPM**:

- epoch
- version
- release
- filename
- checksumtype
- checksum

**RPM, SRPM**:

- name
- epoch
- version
- release
- arch
- checksumtype
- checksum

**ISO**:

- name
- checksum
- size

**Python package**:

- filename

**Puppet module**:

- author
- name
- version

**OSTree branch**:

- remote_id
- branch
- commit

**Docker Blob, Manifest, ManifestList**:

- digest

**Docker Image**:

- image_id

**Docker Tag**:

- name
- repo_id
- schema_version
- manifest_type

**Debian Package**:

- name
- version
- architecture
- checksumtype
- checksum

**What happens when a source repository changes the checksum type that is
published in the repository?**

Since the checksum is one of the attributes used to determine uniqueness, Pulp
assumes that a package published with a sha256 checksum is different from a
package published with a sha512 checksum. As a result, if a source repository
switches the type of checksum it publishes, Pulp will treat all the packages
in that repository as new. This can result in duplicate content being stored
in Pulp.

**How Pulp keeps track of units that belong to a particular repository?**

Each repository is stored as a document in the ``repos`` MongoDB collection.
Each content type is stored in a collection with a prefix of ``units_``.
Relationships between content and repositories are stored in the
``repo_content_units`` collection.

**How symlinks are generated during a repository publish?**

Pulp deduplicate content when possible. As a result, all content units are
stored in one place. Published content is actually a symlink to a content unit
stored elsewhere on disk. When publishing a repository, Pulp uses the
relationships stored in the ``repo_content_units`` for a particular repository
to determine which symlinks need to be published.