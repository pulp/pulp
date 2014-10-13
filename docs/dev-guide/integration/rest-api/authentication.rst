Authentication
==============

Calls to the REST API must be authenticated as a :ref:`User <user>`.

Basic Authentication
--------------------

Any call to the REST API may use
`HTTP basic authentication <http://tools.ietf.org/html/rfc1945#section-11.1>`_
to provide a username and password.

User Certificates
-----------------

You can "login" to Pulp by providing basic auth credentials and receiving a
client SSL certificate to use for future requests. Although this is a POST
operation, there is no data required in the request. The resulting certificate
can then be used as a client-side SSL certificate for authentication of future
requests to the REST API.


| :method:`post`
| :path:`/v2/actions/login/`
| :permission:`read`

| :response_list:`_`

    * :response_code:`200,credentials were accepted`
    * :response_code:`401,credentials were not accepted`


| :return:`response body contains a client SSL certificate and private key`

:sample_response:`200` ::

 {
  "key":
    "-----BEGIN RSA PRIVATE KEY-----
    MIICXAIBAAKBgQC/AW1iSiMbwAeHJcwCQedMHaKg8/3aBA88pkYGwJL1cxlmN5Hr
    OL2WYUi3Kbkt51n56LiBc5wetQ3O2WDARaLTuk4j9LJDVsN065F6q4NuwYLx8lar
    U5ZQVfxE/CP/2KW2ymp4YPFksoo1yZJDvComteuVk2n20o4MKtE7VvYCSwIDAQAB
    AoGAfeJ57hLAitSH4ZmWmFJJF9BcU8obH2oXhLhtZJvc/2npboXnZOjTgt4BJ76W
    7lsQ4PVxTNgeJ9raC98WtgHvKooTyPagIudVBFMszTbseJU7XV8gfC66sG/j4h5U
    d9eJDClgjHbPTSgzFG4Y4Wv/2s4wMl8S/1t0svV4QiS/cdECQQDrGZ5qoV8mWNMp
    gl9NanpfhyRCej0bpdAJ/BDfrYuuE9FJ8r108cDVlIM+XWV6vRGi2W05YZBo7ys/
    KPg/PiDpAkEAz/xPkRCmseVQhF8I2oXAYEbnx7Yxwc+6/MYyc0zK7I03TuEQUHd1
    TfFNSCjkjnrbiTkwU+JrAlgjhRvnYsppEwJABa6o1Yrw8cxTzj0IcKaSLpzlk3XA
    5FotnRAqmD1pktuHw3HKgnkVYBQm1+sJ+N14/6ahrTFefCrLsMsctOqbgQJAFhqV
    hjBD1wIs9XR4J2kxkcnXVjU5woRGNhkGQZS2uD8l0p8+sZ6Qe/EaKoIWEEJkVIgc
    Z73Xa49cbwgRJkGmuwJBALEDimytIFUSzXCJZj1s6/5Uvldfae3297pbdU0ByBHf
    /WZ1p6+u8FthSMnmq4DI4UDdxDQfNjHdcGcWPQb4yko=
    -----END RSA PRIVATE KEY-----
    ",
  "certificate":
    "-----BEGIN CERTIFICATE-----
    MIICMzCCARsCASgwDQYJKoZIhvcNAQEFBQAwFDESMBAGA1UEAxMJbG9jYWxob3N0
    MB4XDTEzMDIyMjE2MjExOFoXDTEzMDMwMTE2MjExOFowLzEtMCsGA1UEAxMkYWRt
    aW46YWRtaW46NTA1YTJiZDFlMTlhMDA2MzViMDAwMDA5MIGfMA0GCSqGSIb3DQEB
    AQUAA4GNADCBiQKBgQC/AW1iSiMbwAeHJcwCQedMHaKg8/3aBA88pkYGwJL1cxlm
    N5HrOL2WYUi3Kbkt51n56LiBc5wetQ3O2WDARaLTuk4j9LJDVsN065F6q4NuwYLx
    8larU5ZQVfxE/CP/2KW2ymp4YPFksoo1yZJDvComteuVk2n20o4MKtE7VvYCSwID
    AQABMA0GCSqGSIb3DQEBBQUAA4IBAQB1JfB8iVv8m/jqROjU2oKtvBCj5RdBELZp
    tz/9TLXUgg7WpGezGIiKfss+hJW7QV1kuOfYS/5kO5XE8rYKg2FB5Tdx5fs4MTPT
    Th7h+kyg6On8y2o1J/uCQ2PSb3Ex5ajbY+PBNqWngcPLIi+Xn0iRmJmgRUO7QZ08
    GXqvcA0wsM0+07WcMNINxfQ1RuEmxWPNtJ861akNyGP8ZsmT0ABd5Q+pUq/nuBQ9
    7jwhi90WftYsQDHik9Ek43ltDVjfhDhQFWg3QKM7Xg2BkYkYYGB6ld6+v/jpOxtp
    Bg9xsQGTzaPcxGKAAwRHnEJ8vcBK+DIH5CqKOmhxxEveBDFWSNAI
    -----END CERTIFICATE-----
    "
 }


