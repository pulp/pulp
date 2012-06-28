# This should be enhanced so a flag can be passed to automatically accept
# the changelog entry or prompt on each. I don't have the time right now and
# we're debugging the new RPMs so I left it in by default.
#
# Also, when adding that flag, don't forget to delete the above comment. :)

GIT_ROOT=`pwd`

for SUBPROJECT in platform rpm-support builtins products/pulp-rpm-product
do
  cd $SUBPROJECT
  tito tag --accept-auto-changelog && git push && git push --tags
  cd $GIT_ROOT
done
