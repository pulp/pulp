Database Field Translation Guide
================================

Introduction
------------

Converting from mongo to postgres should be recognized from the outset as a monumental task.
In choosing Django as our ORM, this task has hopefully been made a little bit easier by bringing in
such a mature and well-supported framework. Great care has been taken to make full use of Django's
offerings when coming up with techniques and guidelines for converting our non-relational mongo
database over to postgres.

Django
------

Django has many layers, including the data model layer, the view layer, etc. This document focuses
on the model layer, and uses Django's terminology where applicable. Furthermore, every effort should
be made to adhere to existing Django functionality so that the full benefits of adopting this
framework can be realized.

https://docs.djangoproject.com/en/1.8/topics/db/models/

Tutorial
^^^^^^^^

If you aren't already familiar with some of the features that Django provides, part 1 of the Django
tutorial provides an excellent introduction. It covers things like starting a project for the first
time, starting the development web server, and accessing models. The tutorial pages that come after
part 1 are largely irrelevant for Pulp 3, but are a good exercise nonetheless for someone looking to
get to know Django a little bit better.

https://docs.djangoproject.com/en/1.8/intro/tutorial01/

Django Concepts
---------------

There are specific Django concepts that deserve special attention before getting into some of the
finer details of how the relation data model should be structured, which are outlined in subsections
below.

Model Inheritance
^^^^^^^^^^^^^^^^^

https://docs.djangoproject.com/en/1.8/topics/db/models/#model-inheritance

Django provides three different mechanisms for supporting object-oriented inheritance in its
Model classes. Each method provides specific benefits to Pulp that are outlined here.

Additionally, each of these model inheritance mechanisms can be combined with the other mechanisms
as-needed to create a sound object-oriented design that also generates a reasonable database schema.

Abstract Base classes
*********************

https://docs.djangoproject.com/en/1.8/topics/db/models/#abstract-base-classes

Many of our ContentUnit classes have common fields and/or behavior. Abstract base classes make it
trivial for us to put those common bits of code in a single place, to be inherited by Model classes in
completely standard and pythonic ways, such as with subclassing or mixins.

The many different RPM-like ContentUnit subclasses use this extensively, combining in the
"detail" classes to make the complete unit model for a given type.

Multi-table Inheritance
***********************

https://docs.djangoproject.com/en/1.8/topics/db/models/#multi-table-inheritance

This is probably the most important Model inheritance mechanism, as it is used to implement the
ContentUnit "master-detail" relationship, where the "master" content units contain all fields
common to all (or most) ContentUnits, and the "detail" content units contain all of the type-specific
fields for that unit type.

On the database level, the information representing a ContentUnit resides in at least two database
tables (the master ContentUnit table and the detail table), and is seamlessly joined by Django on
instances of the detail ContentUnit model (e.g. RPM, a puppet Module, etc).

More information on this is documented later in the section describing ContentUnit changes.

.. note::
    If you go by what wikipedia has to say about master-detail relationships, this isn't quite that.
    However, it makes it easy to refer to both sides of the master/detail relationship with terms that
    are easy to understand in the context of ContentUnits, so it's worth appropriating those
    terms for Pulp's purposes here.

    https://en.wikipedia.org/wiki/Master%E2%80%93detail_interface#Data_model

Proxy Models
************

https://docs.djangoproject.com/en/1.8/topics/db/models/#proxy-models
https://docs.djangoproject.com/en/1.8/topics/db/queries/#backwards-related-objects

Not currently used in Pulp, but mentioned here for docs completeness.

Generic Relations
^^^^^^^^^^^^^^^^^

https://docs.djangoproject.com/en/1.8/ref/contrib/contenttypes/#generic-relations

Django's Generic Relations give us the ability to associate many models to one model in a more
flexible was than a normal ForeignKey. Normally used for things like object tagging,
the Generic Relations that come with Django's contenttypes framework can be used by Pulp to easily
associate a generic Django Model with any number of other models that can benefit from storing the
information captured by the generic model.

A good example of this are the various Generic Key/Value stores that can be associated with any other
Model, "Notes", "Config", and "Scratchpad".


MongoEngine to Django Field Conversions
---------------------------------------

These are the MongoEngine field types currently used by Pulp, and guidelines on converting them to
Postgres. Since MongoEngine started out to get mongodb working as a Django backend, most fields have
direct counterparts in Django. The following subsections are the MongoEngine fields currently used in
Pulp, with applicable postgres datatypes and Django field alternatives listed inside.

In each MongoEngine field section there will be a link to that MongoEngine field's documentation,
brief information about the corresponding postgres data type, subsections detailing the Django
field or fields that should be used when translating a given MongoEngine field, and a list of
files in which that MongoEngine field is being used.

StringField
^^^^^^^^^^^

http://docs.mongoengine.org/apireference.html#mongoengine.fields.StringField

This field can be represented by one of two Django fields, depending on which Postgres column is a
better fit for the data being stored in it.

Postgres datatype reference:
https://www.postgresql.org/docs/current/static/datatype-character.html

For our purposes, only varchar and text are interesting, the character type will be ignored. While
some database engines have differences in performance between the varchar and text data types,
this tip from the linked postgres docs is good to keep in mind:

.. note::
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

CharField
*********

https://docs.djangoproject.com/en/1.8/ref/models/fields/#charfield

Represented by a varchar field in postgres, the max_length argument is required.

When the maximum length of a string is known, such as when storing hash values of a known type (or
types), this is the field to use. String length validation is done at the database level.

TextField
*********

https://docs.djangoproject.com/en/1.8/ref/models/fields/#textfield

Represented by a text field in postgres.

When the maximum length of a string is unknown, such as when storing large chunks of text like errata
descriptions/summaries, this is the field to use.

IntField
^^^^^^^^

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

IntegerField, SmallIntegerField, BigIntegerField
************************************************

https://docs.djangoproject.com/en/1.8/ref/models/fields/#integerfield
https://docs.djangoproject.com/en/1.8/ref/models/fields/#smallintegerfield
https://docs.djangoproject.com/en/1.8/ref/models/fields/#bigintegerfield

2-byte, 4-byte, and 8-byte (respectively) storage for signed integers.

PositiveIntegerField, PositiveSmallIntegerField
***********************************************

https://docs.djangoproject.com/en/1.8/ref/models/fields/#positiveintegerfield
https://docs.djangoproject.com/en/1.8/ref/models/fields/#positivesmallintegerfield

Positive-only variants of SmallIntegerField and IntegerField. These use the
same postgres data types as their non-"Positive" counterparts, but use database
validation to enforce values >= 0.

FloatField
^^^^^^^^^^

http://docs.mongoengine.org/apireference.html#mongoengine.fields.FloatField

Also numeric types, just like IntField and LongField, but there are some python representation options
when it comes to floats that are available in django fields.

https://www.postgresql.org/docs/current/static/datatype-numeric.html

Used in:
- `pulp_rpm/plugins/pulp_rpm/plugins/db/models.py`

FloatField
**********

https://docs.djangoproject.com/en/1.8/ref/models/fields/#floatfield

Stored as the "double precision" data type, using 8 bytes of storage. Represents the python "float"
type.

DecimalField
************

https://docs.djangoproject.com/en/1.8/ref/models/fields/#decimalfield

Stored as the "numeric" data type, storage size varies based on the field precision declared when the
field is created. Very similar to FloatField, but values are represented by the python
"decimal.Decimal" type. Use this field instead of FloatField in cases where the "decimal.Decimal"
type is more appropriate.

For reference: https://docs.python.org/3/library/decimal.html

The postgres docs state that "The actual storage requirement is two bytes for each group of four
decimal digits, plus three to eight bytes overhead," so there's no obvious storage efficiency benefit
the be gained by using this field.

BooleanField
^^^^^^^^^^^^

http://docs.mongoengine.org/apireference.html#mongoengine.fields.BooleanField

A normal BooleanField, represented a True/False value in python.

https://www.postgresql.org/docs/current/static/datatype-boolean.html

Used in:
 - `pulp_rpm/plugins/pulp_rpm/plugins/db/models.py`
 - `pulp/server/pulp/server/db/model/__init__.py`

BooleanField, NullBooleanField
******************************

Represented by the "boolean" data type in postgres. "BooleanField" stores only True or False,
and cannot be null/None, so a default must be specified. The "NullBooleanField" alternative
additionally allows for null/None values, useful in cases where a boolean value might be
unknown, or not required.

https://docs.djangoproject.com/en/1.8/ref/models/fields/#booleanfield
https://docs.djangoproject.com/en/1.8/ref/models/fields/#nullbooleanfield

DateTimeField, UTCDateTimeField, ISO8601StringField
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

DateTimeField
*************

https://docs.djangoproject.com/en/1.8/ref/models/fields/#datetimefield

Represented in postgres as the "timestamp with time zone" data type. Django is configured
to use the UTC timezone, so tz-aware datetime objects will be properly converted to
UTC timestamps when stored, our custom UTCDateTimeField is not required with Django.

DateField, TimeField
^^^^^^^^^^^^^^^^^^^^

MongoEngine does not provide equivalents for these field types, but they're worth mentioning
in the event that only a date or time component of a datetime object needs to be stored.

https://docs.djangoproject.com/en/1.8/ref/models/fields/#datefield

DateField represents the postgres "date" data type, and is the "datetime.date" type in python.

https://docs.djangoproject.com/en/1.8/ref/models/fields/#timefield

TimeField represents the postgres "time" data type, and is the "datetime.time" type in python.
Unlike DateTimeField, TimeField appears to be unaware of time zones; the column type is
"time with

UUIDField
^^^^^^^^^

http://docs.mongoengine.org/apireference.html#mongoengine.fields.UUIDField

UUIDs, represented by instances of the "uuid.UUID" data type.

Used in:
 - `pulp/server/pulp/server/db/model/__init__.py`

UUIDField
*********

https://docs.djangoproject.com/en/1.8/ref/models/fields/#uuidfield

Postgres has native support for UUIDs with the "uuid" data type, storing the value
as the UUID's 128-bit/16-byte value, rather than the UUID string representation.

All models in Pulp 3 also use a UUIDField as their Primary Key by default.

ListField
^^^^^^^^^

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

DictField
^^^^^^^^^

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

UUID Primary Keys
-----------------

Postgres has native support for the UUID datatype, as does Django, making a UUID a viable option
for primary keys. UUIDs are already being used at the de-facto Primary Key of the MongoEngine
ContentUnit. Keeping these UUIDs when migrating to Postgres makes it so that users integrating with
Pulp will be able to keep any references they may have in their own data stores to Pulp ContentUnit
by their existing UUID PK.

Master and Detail ContentUnit Types
-----------------------------------

The "master" ContentUnit model (ContentUnit itself) has some special behaviors added to accomodate
the master-detail inheritance implementation. ContentUnit instance have a `cast` method that will
return a "detail" instance of a ContentUnit type, e.g. the RPM instance for that ContentUnit. Calling
`cast` on a detail instance will return that instance, making `cast` idempotent.

Similarly, all ContentUnits have a `content_unit` property that, when accessed, will always be the
master ContentUnit instance. It functions similarly to `cast`, in that it is idempotent. This is a
property, not a method, because all detail ContentUnit instances are already ContentUnits in an
object-oriented sense, whereas `cast`-ing ContentUnits will most likely result in a database JOIN
operation.

ListField Conversion Example (Errata)
-------------------------------------

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
