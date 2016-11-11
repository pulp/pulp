REST API Reference
==================

All REST API endpoints are protected with basic authentication. The password for the "admin"
user can be set using two methods.

    ``python manage.py reset-admin-password``

The above command prompts the user to enter a new password for "admin" user.

    ``python manage.py reset-admin-password --random``

The above command generates a random password for "admin" user and prints it to the screen.