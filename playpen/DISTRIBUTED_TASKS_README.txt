If you find yourself needing to work in our
distributed-tasks branch, there are a few things you will need to do in
order to get up and running.

1) Disable qpidd (Optional. We still support qpidd for consumers, in addition to rabbitmq.)

    $ sudo systemctl stop qpidd

    $ sudo systemctl disable qpidd

2) Install and start RabbitMQ:

    $ sudo yum install rabbitmq-server

    If you didn't disable qpidd, you will need to configure Rabbit to run on a different port, as
    they both use the same port by default. Put the following into /etc/rabbitmq/rabbitmq-env.conf:

        NODE_PORT=<insert port you want here>

    $ sudo systemctl enable rabbitmq-server

    $ sudo systemctl start rabbitmq-server

    Add a rabbit user. You will need to remember the username and password you set here for the
    broker_url in step 3.

    $ sudo rabbitmqctl add_user <username> <password>

    Optionally, you can create a vhost here. If you do, you need to put it in the <vhost> part of
    the broker_url in step 3. If you don't, leave the trailing slash on the broker_url, but put
    nothing.

    $ sudo rabbitmqctl add_vhost <vhost>

    If you added a vhost, you need the -p <vhost> part of this next command, and if you didn't,
    simply omit that portion.

    $ sudo rabbitmqctl set_permissions -p <vhost> <username> ".*" ".*" ".*"

3) Edit Pulp's server.conf to reflect the correct settings for the consumer (if you disabled qpidd),
   and for the new tasking system.

   [tasks]
   broker_url: amqp://<username>:<password>@<hostname>:<port>/<vhost>

   Don't forget to update the [messaging] section if you aren't using qpidd anymore. I'm not sure
   what goes there, so ask jortel :)

4) Now you must install Celery and start at least three celeryd's. Currently, the Celery packages in
   both EPEL and Fedora cannot be used with Pulp, so you will need to install
   Celery with pip. I recommend keeping each celeryd in it's own terminal
   for fun, but do what you like. Also, the --loglevel can be seasoned to taste. INFO will print out
   each task that was accepted, and will also note when they complete and how long they took. I
   think the default loglevel doesn't print anything unless there's a problem or a print statement.

     This first one is the general celeryd that takes on "normal" tasks. You only need to start one
     of these, and it will default to a concurrency level equal to the number of cores you have.

     $ celeryd -A pulp.server.async.app --loglevel INFO

     Secondly, you will need at least one celeryd to do the work of the reserved tasks. This is very
     important, as reserved tasks will just pile up if there isn't at least one process around to
     deal with them. Start as many of these as you like, but take care to assign them all the -c 1
     flag (concurrency of 1), and make sure they have unique names. Each of them must be named (with
     the -n flag) with the prefix "reserved_resource_worker-". The resource manager will look for
     workers with names that start with that prefix to identify that they wish to perform these
     duties. If you want them to only process reserved work, you should use the -Q flag to assign
     them to queues of their own name. If you don't supply the -Q flag, the resource_manager will
     automatically subscribe them to their own queue, and they will also be subscribed to the
     general Celery queue. I (rbarlow) recommend leaving the -Q flag off so they can perform work
     from both queues, but feel free to do as you please. This will start two of them, for example:

     $ celeryd -A pulp.server.async.app --loglevel INFO -c 1 -n reserved_resource_worker-1

     $ celeryd -A pulp.server.async.app --loglevel INFO -c 1 -n reserved_resource_worker-2

     The last one is the ReservationManager. It is very important, as its job is to route tasks
     that reserve resources to the correct workers. You can adjust the -n flag to whatever you like,
     but it is critical that you do not change the -c or -Q flags on this command.

     $ celeryd -A pulp.server.async.app --loglevel INFO -c 1 -n resource_manager -Q resource_manager

5) Lastly, you need to run a Celery Beat. This is similar to a crond for Celery. It is important
   that only one Celery Beat be run across the entire application, no matter how many Pulp servers
   are part of the system.

   $ celery beat -A pulp.server.async.app --loglevel INFO

I believe that is all that is required to get up and running with Celery in Pulp at the moment. We
plan to develop a way to package all of this and make it really easy for our users in a future
sprint, so that users will not need to perform the operations in step 4. Happy coding, and feel free
to ask if you have questions, or to update this document if you feel more info would be helpful, or
if you find a mistake.
