# This should be enhanced so a flag can be passed to automatically accept
# the changelog entry or prompt on each. I don't have the time right now and
# we're debugging the new RPMs so I left it in by default.
#
# Also, when adding that flag, don't forget to delete the above comment. :)

GIT_ROOT=`pwd`
TAG_FLAGS="--accept-auto-changelog"
PUSH_FLAGS="--tags"

for SUBPROJECT in platform rpm-support builtins products/pulp-rpm-product
do
  pushd $SUBPROJECT
  echo "tagging $SUBPROJECT"
  tito tag $TAG_FLAGS && git push && git push $PUSH_FLAGS
  popd
done
