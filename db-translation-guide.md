Relational Pulp Translation Guide

# Introduction

Converting from mongo to postgres should be recognized from the outset as a monumental task.
In choosing Django as our ORM, this task has hopefully been made a little bit easier by bringing in
such a mature and well-supported framework. Great care has been taken to make full use of Django's
offerings when coming up with techniques and guidelines for converting our non-relational mongo
database over to postgres.

This document intends to serve as a reference guide for developers taking on this conversion task,
with particular focus on Repositories and Content Units. This should be considered a living
document: we should keep it up to date with current development practices.

This document does not intend to take on other aspects of the move to Pulp 3, such as the REST API,
the plugin API, the tasking system, RBAC, search, or other aspects of Pulp 3 that are likely to be
completely revamped/replaced rather than migrated.

Many links are provided in-line to relevant documentation that can be used to aid in translating
MongoEngine Documents to Django Models. This document avoids repeating information found at these
links, opting instead to point out how the information at these links applies to Pulp and its
transition to a relational database.

## What is "Relational Pulp"?

https://github.com/seandst/relational-pulp/

We currently have no strategy for updating our codebase from Pulp 2 to Pulp 3, and Django is so
drastically different from MongoEngine (and pymongo) that iteratively converting Pulp in-place from
mongo to postgres looks very difficult. The Relational Pulp project aims to reimplement the Pulp 2
data model using the Django framework and sound relational design, and provide a useful and working
code base that can be used when we do have a strategy for how to get from Pulp 2 to Pulp 3 as
developers. How the code base gets used depends on that strategy, so at the moment the relational
Pulp project is little more than a sandbox/testbed for proving the viability of converting Pulp to
a relational database.

All of the findings documented here are the result of work on the Relational Pulp project, and are
subject to change (but hopefully not a lot) as requirements are discovered, clarified, or otherwise
altered as part of the Pulp 3 development effort.

# Postgres

While we are targeting postgres specifically for Pulp 3, no postgres-specific
functionality should be needed to migrate Pulp to a relational database, allowing for a database-
agnostic data model. This is analogous to using celery with kombu, allowing Pulp to (probably!)
function on any backend supported by kombu, rather than explicitly coding Pulp to work on qpid.
All of the links in this document are to the "current" version of postgres, but all of the features
described in this document are written under the assumption that postgres 8.4 or higher will be
available.

While being database-agnostic is a laudable goal, it is not a hard requirement for Pulp 3. In the
event that postgres provides some django-supported "killer feature", we can drop database-agnosticism
as a goal.

https://www.softwarecollections.org/en/scls/rhscl/rh-postgresql94/

    That all said, full-text search is a pretty killer feature, and might lock us to postgres anyway.
    This feature appears in Django 1.10 and might end up forcing us to completely rewrite this
    section and the Django Version section of this document. Figuring out how to do search is a
    big next step for Pulp 3, and has not been thoroughly investigated as part of the Relational
    Pulp effort.

    https://docs.djangoproject.com/en/dev/ref/contrib/postgres/search/

# Django

Django has many layers, including the data model layer, the view layer, etc. This document focuses
on the model layer, and uses Django's terminology where applicable. Furthermore, every effort should
be made to adhere to existing Django functionality so that the full benefits of adopting this
framework can be realized.

https://docs.djangoproject.com/en/1.8/topics/db/models/

## Tutorial

If you aren't already familiar with some of the features that Django provides, part 1 of the Django
tutorial provides an excellent introduction. It covers things like starting a project for the first
time, starting the development web server, and accessing models. The tutorial pages that come after
part 1 are largely irrelevant for Pulp 3, but are a good exercise nonetheless for someone looking to
get to know Django a little bit better.

https://docs.djangoproject.com/en/1.8/intro/tutorial01/

## Version

At the moment, Django 1.8 is the front-runner for our Django version of choice. All links to
Django documentation are directed to Django 1.8 as a result.

Pros:
- Most recent "LTS" release of Django.
- Supports Postgres 9+, which is available in every distribution Pulp supports.

Cons (sorta):
- Not the latest version, so we miss out on specific features
  - ...but we gain API stability in return
- Requires using SCLs on distributions that don't provide postgres 9
  - ...but we also need SCLs for python if we support el6

## Django Concepts

There are specific Django concepts that deserve special attention before getting into some of the
finer details of how the relation data model should be structured, which are outlined in subsections
below.

### Model Inheritance

https://docs.djangoproject.com/en/1.8/topics/db/models/#model-inheritance

Django provides three different mechanisms for supporting object-oriented inheritance in its
Model classes. Each method provides specific benefits to Pulp that are outlined here.

Additionally, each of these model inheritance mechanisms can be combined with the other mechanisms
as-needed to create a sound object-oriented design that also generates a reasonable database schema.

#### Abstract Base classes

https://docs.djangoproject.com/en/1.8/topics/db/models/#abstract-base-classes

Many of our ContentUnit classes have common fields and/or behavior. Abstract base classes make it
trivial for us to put those common bits of code in a single place, to be inherited by Model classes in
completely standard and pythonic ways, such as with subclassing or mixins.

The many different RPM-like ContentUnit subclasses use this extensively, combining in the
"detail" classes to make the complete unit model for a given type.

#### Multi-table Inheritance

https://docs.djangoproject.com/en/1.8/topics/db/models/#multi-table-inheritance

This is probably the most important Model inheritance mechanism, as it is used to implement the
ContentUnit "master-detail" relationship, where the "master" content units contain all fields
common to all (or most) ContentUnits, and the "detail" content units contain all of the type-specific
fields for that unit type.

On the database level, the information representing a ContentUnit resides in at least two database
tables (the master ContentUnit table and the detail table), and is seamlessly joined by Django on
instances of the detail ContentUnit model (e.g. RPM, a puppet Module, etc).

More information on this is documented later in the section describing ContentUnit changes.

    If you go by what wikipedia has to say about master-detail relationships, this isn't quite that.
    However, it makes it easy to refer to both sides of the master/detail relationship with terms that
    are easy to understand in the context of ContentUnits, so it's worth appropriating those
    terms for Pulp's purposes here.

    https://en.wikipedia.org/wiki/Master%E2%80%93detail_interface#Data_model

#### Proxy Models

https://docs.djangoproject.com/en/1.8/topics/db/models/#proxy-models
https://docs.djangoproject.com/en/1.8/topics/db/queries/#backwards-related-objects

Proxy models have no effect on the database. They have all of the same database state as the models
they proxy back to, only the behavior is changed. Proxy models are a convenient middle ground between
typed and untyped repositories, and solve this potential namespacing issue:

When creating relationships between Django models, Django does us a favor, and creates what is known
as a "reverse relation" on the object bein related *to*. The reverse relation is created on the
relationship's target model automatically. Creating several models that relate to Repository, for
example, will create several of these reverse relations on the Repository model, cluttering its
namespace. One solution, involving a proxy model, would be to create a plugin-specific
repository proxy model (e.g. RPMRepositoryProxy for the RPM plugin), and then any Model in the RPM
plugin that would ForeignKey to Repository targets that proxy model instead. The reverse
relations will be created on the proxy model, but the "normal" Repository model is unaffected.

Sticking with Repository for another example, an RPMRepositoryProxy also gives us the ability to add
RPM-specific methods, properties, etc to a Repository without making any changes to the platform
Repository API.

    RPMRepositoryProxy is not really a typed repository, per se. Its name, following the scheme of
    <plugin>RepositoryProxy, still allows for an "RPMRepository" Model to be created at some
    point in the future if/when we implement typed repositories.

### Generic Relations

https://docs.djangoproject.com/en/1.8/ref/contrib/contenttypes/#generic-relations

Django's Generic Relations give us the ability to associate many models to one model in a more
flexible was than a normal ForeignKey. Normally used for things like object tagging,
the Generic Relations that come with Django's contenttypes framework can be used by Pulp to easily
associate a generic Django Model with any number of other models that can benefit from storing the
information captured by the generic model.

A good example of this are the various Generic Key/Value stores that can be associated with any other
Model, "Notes", "Config", and "Scratchpad".

# MongoEngine to Django Field Conversions

These are the MongoEngine field types currently used by Pulp, and guidelines on converting them to
Postgres. Since MongoEngine started out to get mongodb working as a Django backend, most fields have
direct counterparts in Django. The following subsections are the MongoEngine fields currently used in
Pulp, with applicable postgres datatypes and Django field alternatives listed inside.

In each MongoEngine field section there will be a link to that MongoEngine field's documentation,
brief information about the corresponding postgres data type, subsections detailing the Django
field or fields that should be used when translating a given MongoEngine field, and a list of
files in which that MongoEngine field is being used.

## Simple Field Types

These field types are directly supported by postgres/Django, and have a clear migration path.

### StringField

http://docs.mongoengine.org/apireference.html#mongoengine.fields.StringField

This field can be represented by one of two Django fields, depending on which Postgres column is a
better fit for the data being stored in it.

Postgres datatype reference:
https://www.postgresql.org/docs/current/static/datatype-character.html

For our purposes, only varchar and text are interesting, the character type will be ignored. While
some database engines have differences in performance between the varchar and text data types,
this tip from the linked postgres docs is good to keep in mind:

"There are no performance differences between these three types, apart from the increased storage size
when using the blank-padded type. While character(n) has performance advantages in some other database
systems, it has no such advantages in PostgreSQL. In most situations text or character varying should
be used instead."

The "blank-padded" type mentioned in that quote is the character type, so for our purposes there is no
difference in performance between varchar and text.

Used in:
- `pulp_rpm/plugins/pulp_rpm/plugins/db/models.py`
- `pulp_rpm/plugins/pulp_rpm/plugins/db/fields.py`
- `pulp_ostree/plugins/pulp_ostree/plugins/db/model.py`
- `pulp_docker/plugins/pulp_docker/plugins/models.py`
- `pulp_puppet/pulp_puppet_plugins/pulp_puppet/plugins/db/models.py`
- `pulp/server/pulp/server/db/model/__init__.py`
- `pulp/server/pulp/server/db/fields.py`
- `pulp_python/plugins/pulp_python/plugins/models.py`

#### CharField

https://docs.djangoproject.com/en/1.8/ref/models/fields/#charfield

Represented by a varchar field in postgres, the max_length argument is required.

When the maximum length of a string is known, such as when storing hash values of a known type (or
types), this is the field to use. String length validation is done at the database level.

#### TextField

https://docs.djangoproject.com/en/1.8/ref/models/fields/#textfield

Represented by a text field in postgres.

When the maximum length of a string is unknown, such as when storing large chunks of text like errata
descriptions/summaries, this is the field to use.

### IntField

http://docs.mongoengine.org/apireference.html#mongoengine.fields.IntField

There are more numeric types supported by postgres + Django than are offered by MongoEngine,
so converting from one of these MongoEngine fields to a postgres field should take
the available Django field types into account to ensure that the most appropriate
postgres data type is being used.

https://www.postgresql.org/docs/current/static/datatype-numeric.html

The only known MongoEngine FloatField in Pulp is a timestamp field on the Distribution document,
which could reasonably be converted to a DateTimeField.

Used in:
- `pulp_rpm/plugins/pulp_rpm/plugins/db/models.py`
- `pulp_docker/plugins/pulp_docker/plugins/models.py`
- `pulp/server/pulp/server/db/model/__init__.py`

#### IntegerField, SmallIntegerField, BigIntegerField

https://docs.djangoproject.com/en/1.8/ref/models/fields/#integerfield
https://docs.djangoproject.com/en/1.8/ref/models/fields/#smallintegerfield
https://docs.djangoproject.com/en/1.8/ref/models/fields/#bigintegerfield

2-byte, 4-byte, and 8-byte (respectively) storage for signed integers.

#### PositiveIntegerField, PositiveSmallIntegerField

https://docs.djangoproject.com/en/1.8/ref/models/fields/#positiveintegerfield
https://docs.djangoproject.com/en/1.8/ref/models/fields/#positivesmallintegerfield

Positive-only variants of SmallIntegerField and IntegerField. These use the
same postgres data types as their non-"Positive" counterparts, but use database
validation to enforce values >= 0.

### FloatField

http://docs.mongoengine.org/apireference.html#mongoengine.fields.FloatField

Also numeric types, just like IntField and LongField, but there are some python representation options
when it comes to floats that are available in django fields.

https://www.postgresql.org/docs/current/static/datatype-numeric.html

Used in:
- `pulp_rpm/plugins/pulp_rpm/plugins/db/models.py`

#### FloatField

https://docs.djangoproject.com/en/1.8/ref/models/fields/#floatfield

Stored as the "double precision" data type, using 8 bytes of storage. Represents the python "float"
type.

#### DecimalField

https://docs.djangoproject.com/en/1.8/ref/models/fields/#decimalfield

Stored as the "numeric" data type, storage size varies based on the field precision declared when the
field is created. Very similar to FloatField, but values are represented by the python
"decimal.Decimal" type. Use this field instead of FloatField in cases where the "decimal.Decimal"
type is more appropriate.

For reference: https://docs.python.org/3/library/decimal.html

The postgres docs state that "The actual storage requirement is two bytes for each group of four
decimal digits, plus three to eight bytes overhead," so there's no obvious storage efficiency benefit
the be gained by using this field.

### BooleanField

http://docs.mongoengine.org/apireference.html#mongoengine.fields.BooleanField

A normal BooleanField, represented a True/False value in python.

https://www.postgresql.org/docs/current/static/datatype-boolean.html

Used in:
- `pulp_rpm/plugins/pulp_rpm/plugins/db/models.py`
- `pulp/server/pulp/server/db/model/__init__.py`

#### BooleanField, NullBooleanField

Represented by the "boolean" data type in postgres. "BooleanField" stores only True or False,
and cannot be null/None, so a default must be specified. The "NullBooleanField" alternative
additionally allows for null/None values, useful in cases where a boolean value might be
unknown, or not required.

https://docs.djangoproject.com/en/1.8/ref/models/fields/#booleanfield
https://docs.djangoproject.com/en/1.8/ref/models/fields/#nullbooleanfield

### DateTimeField, UTCDateTimeField, ISO8601StringField

http://docs.mongoengine.org/apireference.html#mongoengine.fields.DateTimeField

All mongoengine DateTimeFields should, at this point, be storing UTC datetime
stamps, represented in python as "datetime.datetime" instances. UTCDateTimeField and
ISO8601StringField are custom fields with special behavior for storage, but
all datetimes should be stored in postgres as postgres's native data type, so the only
Django field type we should be using for all of these mongo fields is DateTimeField.
Custom serialization/deserialization of datetime data should be done at the API layer.

https://www.postgresql.org/docs/current/static/datatype-datetime.html

Used in:
- `pulp_ostree/plugins/pulp_ostree/plugins/db/model.py`
- `pulp/server/pulp/server/db/model/__init__.py`
- `pulp/server/pulp/server/db/fields.py`

#### DateTimeField

https://docs.djangoproject.com/en/1.8/ref/models/fields/#datetimefield

Represented in postgres as the "timestamp with time zone" data type. Django is configured
to use the UTC timezone, so tz-aware datetime objects will be properly converted to
UTC timestamps when stored, our custom UTCDateTimeField is not required with Django.

#### DateField, TimeField

MongoEngine does not provide equivalents for these field types, but they're worth mentioning
in the event that only a date or time component of a datetime object needs to be stored.

https://docs.djangoproject.com/en/1.8/ref/models/fields/#datefield

DateField represents the postgres "date" data type, and is the "datetime.date" type in python.

https://docs.djangoproject.com/en/1.8/ref/models/fields/#timefield

TimeField represents the postgres "time" data type, and is the "datetime.time" type in python.
Unlike DateTimeField, TimeField appears to be unaware of time zones; the column type is
"time with

### UUIDField

http://docs.mongoengine.org/apireference.html#mongoengine.fields.UUIDField

UUIDs, represented by instances of the "uuid.UUID" data type.

Used in:
- `pulp/server/pulp/server/db/model/__init__.py`

#### UUIDField

https://docs.djangoproject.com/en/1.8/ref/models/fields/#uuidfield

Postgres has native support for UUIDs with the "uuid" data type, storing the value
as the UUID's 128-bit/16-byte value, rather than the UUID string representation.

## Complex Field Types

These field types are mongo-specific, *do not* have a postgres/Django counterpart.

### EmbeddedDocumentField

http://docs.mongoengine.org/apireference.html#mongoengine.fields.EmbeddedDocumentField

The EmbeddedDocumentField, as the name indicates, stores a document embedded in another
MongoEngine document. To convert to postgres, the embedded document should be properly
modeled as a Django Model, or as part of the Django Model that formerly embedded the
document in MongoEngine.

The only EmbeddedDocumentField in Pulp can be found in the Docker plugin, as an
attribute of the Manifest Document. Its purpose appears to be referential, and can
most likely be replaced with a standard ForeignKey relationship.

Used in:
- `pulp_docker/plugins/pulp_docker/plugins/models.py`

### DynamicField

http://docs.mongoengine.org/apireference.html#mongoengine.fields.DynamicField

DynamicField supports multiple field types as potential values, owing to mongodb's
schemaless nature. Given postgres's schema-full nature, instances of this field
type must be converted to one of the available Django field types.

The only DynamicField in Pulp is in the platform TaskStatus Model, as its "result"
attribute, which will need to be remodeled as part of this transition.

Used in:
- `pulp/server/pulp/server/db/model/__init__.py`

### ListField

http://docs.mongoengine.org/apireference.html#mongoengine.fields.ListField

In general, elements of ListField arrays should be turned into their own
Django Model, with a ForeignKey relationship back to the Model that originally
contained the ListField.

A sort of case-study regarding converting ListFields to models can be found in the
"ListField Conversion Example" section of this document.

Used in:
- `pulp_rpm/plugins/pulp_rpm/plugins/db/models.py`
- `pulp_docker/plugins/pulp_docker/plugins/models.py`
- `pulp_puppet/pulp_puppet_plugins/pulp_puppet/plugins/db/models.py`
- `pulp/server/pulp/server/db/model/__init__.py`

### DictField

http://docs.mongoengine.org/apireference.html#mongoengine.fields.DictField

There are many and varied instances of DictFields in Pulp. DictFields can usually
either be reduced to key/value stores, or should (like with ListField) be turned
into Django Models that ForeignKey back to the Model that originally contained the
DictField. For the case of key/value stores, see the "Arbitrary User Data" section
for details on how to handle that case.

Used in:
- `pulp_rpm/plugins/pulp_rpm/plugins/db/models.py`
- `pulp_ostree/plugins/pulp_ostree/plugins/db/model.py`
- `pulp/server/pulp/server/db/model/__init__.py`

# ContentUnit Changes and Notes

The primary focus of this initial "Relational Pulp" exploration was to address the relationship
between Repositories and ContentUnits. The most notable of those changes, generally those not easily
managed by translating a single field, are outlined here along with general notes about specific
choices that were made along the way.

## UUID Primary Keys

Postgres has native support for the UUID datatype, as does Django, making a UUID a viable option
for primary keys. UUIDs are already being used at the de-facto Primary Key of the MongoEngine
ContentUnit. Keeping these UUIDs when migrating to Postgres makes it so that users integrating with
Pulp will be able to keep any references they may have in their own data stores to Pulp ContentUnit
by their existing UUID PK.

## Master and Detail ContentUnit Types

The "master" ContentUnit model (ContentUnit itself) has some special behaviors added to accomodate
the master-detail inheritance implementation. ContentUnit instance have a `cast` method that will
return a "detail" instance of a ContentUnit type, e.g. the RPM instance for that ContentUnit. Calling
`cast` on a detail instance will return that instance, making `cast` idempotent.

Similarly, all ContentUnits have a `content_unit` property that, when accessed, will always be the
master ContentUnit instance. It functions similarly to `cast`, in that it is idempotent. This is a
property, not a method, because all detail ContentUnit instances are already ContentUnits in an
object-oriented sense, whereas `cast`ing ContentUnits will most likely result in a database JOIN
operation.

In general, `cast`ing units should be avoided, and working directly with the detail unit type will
result in more efficient database operation.

## ContentUnit vs. Repository Metadata

Many Pulp 2 ContentUnit subclasses are actually just metadata related to repositories that provide
additional information or structure about the content stored in that Repository. For example,
a Yum Repository's "comps.xml" contains various lists of packages, but doesn't contain any content
itself. This was most likely done because subclassing ContentUnit in Pulp 2 is the simplest way to
have a Document be related to a Repository. With Django, you just ForeignKey to the Repository
(or to a plugin-specific Repository proxy).

## ContentUnit.repositories

ContentUnits now have a ManyToMany relationship with the Repository instances that contain them,
which Django exposes on ContentUnit instances as related object manager attribute named
"repositories". Similarly, Repository instances have a "units" attribute representing this
relationship.

https://docs.djangoproject.com/en/1.8/ref/models/relations/

While this is a pretty "normal" Django ManyToMany relationship, it bears mentioning here since it's
probably the biggest single reason we're doing all of this.

## ContentUnitFile

In Pulp 2, ContentUnits are generally associated with a single file, but in some cases ContentUnits
have zero, one, or many files associated with them. In Pulp 3, a new "ContentUnitFile" Model has been
created that has a ForeignKey relationship back to ContentUnit. As a result, all ContentUnits can
have zero, one, or many files associated with them without any further customization to ContentUnit
required to deal with it. Since the storage path for a ContentUnitFile is based on the unit key of
its parent ContentUnit, all files associated with a ContentUnit will have the same base storage path.

### Checksums Denormalized?

A closer look at the ContentUnitFile Model shows that there are a number of checksum fields present
on that Model. At first glance, this appears to be a denormalization. There are potentially infinite
checksum types, with some properties of each type unknown. Should this be a related "Checksum" Model,
or maybe some sort of Generic Relation that can handle checksums for all models that need to support
them? Maybe!

In reality, though, the set of checksum types supported by Pulp is finite, and is limited to the
algorithms available when using python's `hashlib` module. Also, each checksum type value
has a known length associated with it. While each checksum type is very similar, they are distinct,
and the number of types is finite. Specifically, the values of `hashlib.algorithms_guaranteed` are
the field attribute names exposed on ContentUnitFile.

Assuming no other model would benefit from these checksum fields, and this appear to be true looking
at how checksums are used in Pulp 2, then exposing the checksums as Model fields is reasonable, and
not a denormalization.

# Arbitrary User Data

Pulp 2 supports arbitrary user data thanks to MongoEngine DictFields. DictFields allow for complex,
nested data structures, with the only requirement be that the values in the field be something that
mongo can store as a BSON object/embdeeded document. Examples include the "notes" and "scratchpad"
fields on some models, and the "pulp_user_metadata" field on ContentUnit.

Pulp 3 will not support arbitrary user metadata. Instead, Pulp 3 will support arbitrary user key/value
pairs, where both keys and values are strings. The migration from Pulp 2 to Pulp 3 will do its best
to convert arbitrary user data to these key/value string pairs by flattening the contents of
MongoEngine DictFields into string key/value representations and storing the result.

# ListField Conversion Example (Errata)

In Pulp 2, the Errata model has many ListFields associated with it:
- references, a list of items to which this Errata refers, such as BZ bugs and CVEs
- pkglist, a list of package collections (themselves a list) referred to by this errata

As a result, both "references" and "pkglist" should become their own Model with a corresponding table
in the database with a ForeignKey relationship back to Errata.  Furthermore, because the "pkglist"
element in updateinfo.xml can contains package collections, another Model is needed to represent
those package collections, which then has a ForeignKey relationship back to the pkglist that contains
it.

To sum up, the single Pulp 2 Errata model, with its two ListFields, becomes four Django Models:
- Errata
  - ErrataReference - Exposed on Errata instances at the "references" attribute
  - ErrataCollection - Exposed on Errata instances as the "pkglist" attribute
    - ErrataPackage - Exposed on ErrataCollection instances as the "packages" attribute

These models (probably!) meet the requirements for errata:
- Pulp can store all data found in errata updateinfo XML files when syncing repos.
- Pulp can generate equivalent updateinfo XML files when publishing repos.

# Model-writing "Do"s and "Don't"s

None of these are official policies. Instead, they are intended to be helpful guidelines that can
assist in decision making when translating MongoEngine Documents to Django Models.

## Do...

### Do Reduce, Reuse, Recycle

As described in the "Model Inheritance" section, Django makes it possible for us to use
good object-oriented design to create a good relational database design. Make use of good OO
principles to avoid duplicating work that's already been done, or can be done in common ancestors.

### Do Let Django do it Django's way

Related to the previous point, most of the problems encountered in using a relational data model are
well known, and solutions to them exist in the Django ORM. Before spending a lot of time implementing
an intricate solution to a tricky problem, make sure Django doesn't already provide a solution to the
problem at hand.

Django's docs are very good, but they aren't always organized in the most intuitive way. It can be
difficult to find the documentation related to the specific problem at hand, but it's worth the effort
to look and ask around to make Django doesn't already have a solution before implementing something
custom.

### Do Make tables

Don't be afraid to make tables, especially when breaking down complex mongo fields into
Django Models with simple field types. Most, if not all, MongoEngine ListFields will end up
becoming *at least* one postgres table.

### Do Make columns

Pulp should not be the arbiter of what information is or is not interesting to its users on a
ContentUnit. As a result, Pulp should attempt to store as much available data as possible in a
ContentUnit's detail table from that ContentUnit's data source(s) while still keeping a good and
consistent data model.

### Do Forget about the API Representation

Store data in the database column type best suited for that data, regardless of how it might
need to be represented in the API. The API layer depends on the data model layer, but the data model
layer **does not** depend on the API layer.

The data model layer should be entirely focused on being a good model, written as good python.
The API layer will do what it needs to represent database values properly to users.

### Do Care about uniqueness for detail ContentUnit types

> *alternate heading: "postgres doesn't solve the duplicate NEVRA problem"*

Uniqueness contraints don't cross table boundaries, so there's no simple way to enforce
ContentUnit-specific constraints at a database level, such as enforcing the uniqueness of fields
in a content unit's unit key in a single repository. (e.g. All NEVRA in a repository are unique.)

Django does provide a mechanism for validating uniqueness in "special" ways, but this is part of
Django's validation system which may not always be called if we're using custom views (which we will).

https://docs.djangoproject.com/en/1.9/ref/models/instances/#django.db.models.Model.validate_unique

`validate_unique` is clearly the correct place to enforce correct uniqueness for model instances, but
we will still need to have mechanisms in place to ensure it is being called at the correct times.

## Don't...

### Don't Use Meaningful Primary Keys

DB primary keys should not be meaningful in any context other than relations between tables. The
properties that make primary keys interesting as identity fields, which is that they are unique,
indexed, and not NULL, are all properties that can be individually or collectivley assigned to most
Django model fields. Separating an object's *meaningful* identity from its *referential* identity (its
otherwise meaningless primary key) frees us to be able to change that object's meaningful identity, if
required, in the future.

For example, a repository's meaningful identity is its repo_id. Making the repo_id field the primary
key of a Repository would make it difficult to rename a repository, if that ever became a requirement
that Pulp wanted to fulfill.

If a meaningful natural key is desired for a Model (and it should be, this is nice to have),
implement a natural key on your Model:
https://docs.djangoproject.com/en/1.8/topics/serialization/#natural-keys

### Don't Index everything

Indexes are mainly used to find rows in a database quickly. If a field is not normally used to
identify a particular row (or particular rows), it probably doesn't need an index. If implementing
nature keys, a subset of those natural keys should be indexed.

For example, in the set of NEVRA fields, "name" is very likely to be used to find a set of rows in the
RPM unit's detail table. None of the remaining fields are likely to be used separate from the "name"
field to locate RPMs (epoch, version, releas, arch).

### Don't *Arbitrarily* denormalize relations

In the relational context, normalization is a Good Thing. However, there may be times where strict
normalization might seem cumbersome, and a desire to "denormalize" relations creeps into the design
process. Sometimes denormalization is absolutely the right solution, but often it will be an
instance of premature optimization. Unless a normalized relationship proves to be too slow, too
cumbersome, or otherwise less useful than desired, avoid the temptation to fix something that may
not be broken.
