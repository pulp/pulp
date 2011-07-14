export MONGO_DB_SERVER="localhost"
export MONGO_DB_SERVER_PORT="27017"
export PULP_DB_NAME="pulp_database"

mongo ${MONGO_DB_SERVER}:${MONGO_DB_SERVER_PORT}/${PULP_DB_NAME} display_largest_event_documents.js

