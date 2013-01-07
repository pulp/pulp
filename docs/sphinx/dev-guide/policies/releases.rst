Release Management
==================

Branch Management
-----------------

To create a new release branch, follow these steps.

1. Create a new branch from master called "pulp-x.y".

2. In master, bump all versions to x.(y+1).

Work can now continue as normal. Bug and feature branches can branch from the
"pulp-x.y" branch and be merged into both "pulp-x.y" and master.

When it is time to release version x.y.(z+1), follow these steps.

1. make sure pulp-x.y is fully merged into master.

2. Follow the release steps, which will bump version numbers and grow the
   change log.

3. Merge pulp-x.y into master (and every release branch greater than x.y)
   using the "ours" strategy. This ignores the file
   changes from step 2, but makes sure that pulp-x.y is still fully merged into
   master.

 ::

   $ git checkout master
   $ git merge -s ours pulp-2.0


.. note::

 The "ours" strategy merges from the specified branch, but it ignores all changes
 from that branch. Thus, each change set from pulp-x.y will become a part of the
 master branch's history, but the actual code changes that took place will not
 be applied to the master branch.

 If step 3 were not performed, every future branch of pulp-x.y would have a conflict
 with master over the version and changelog. Merging immediately after the release
 with the "ours" strategy effectively resolves that conflict.
