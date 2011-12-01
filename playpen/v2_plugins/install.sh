echo "Creating symbolic links for harness plugins into /var/lib/pulp/plugins"
ln -s `pwd`/distributors/* /var/lib/pulp/plugins/distributors/
ln -s `pwd`/importers/*    /var/lib/pulp/plugins/importers/
ln -s `pwd`/types/*        /var/lib/pulp/plugins/types/
