Content Support Packages
========================

Support for specific types of content are provided by *Content Support Packages*. Each
package includes the content type definition, server plugins, agent handlers and CLI extensions.
After the installation or update of a content support package, users must do the following:

* Run ``pulp-manage-db`` to ensure the content definition has been added or updated.
* Restart all :doc:`platform services<services>`.
