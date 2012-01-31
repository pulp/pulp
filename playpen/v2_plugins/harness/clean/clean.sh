echo "Purging the database of repositories and content units"
mongo localhost:27017/pulp_database db-clean.js
