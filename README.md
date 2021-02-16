# Checks a web status and store it into a DB

It's split into two components. One is the producer, which performs the web checking and then publish the result to a kafka server. The second is the consumer that is in charge of receive these messages and store them into a postgres db.

## Development

### Dependencies needed

You will need docker running, docker-compose and, make installed.

### Running test cases

Assuming you have the dependencies satisfied, just execute the target `make test` for running the test cases. It will launch some containers described in the `docker-compose.yaml` file and then execute the tests inside of a container with the Python dependencies needed. You will the the following output

```sh
make test
.......
----------------------------------------------------------------------
Ran 7 tests in 3.761s

OK
```

### Testing/developing consumer and producer

Using docker-compose is the easiest way. First execute `make up` to have all the containers needed (zookeper, kafka, and postgres) running. Then launch two terminals e.g. `docker-compose exec webchecker bash`, dedicating one terminal for the producer and the other one for the consumer.

It's a single app with two subcommands (producer and consumer). Following the help would give you a quick hint how to launch them.

```sh
$ python3 src/webcheck.py -h
usage: webcheck.py [-h] -k KAFKA_URL {consumer,producer} ...

Checks periodically a web site passed as parameter

positional arguments:
  {consumer,producer}   Sub-commands
    consumer            Receives data from kafka and saves data into db
    producer            Performs a GET request and submits data to kafka

optional arguments:
  -h, --help            show this help message and exit
  -k KAFKA_URL, --kafka-url KAFKA_URL
                        Kafka url, it can be passed multiple times, e.g. --kafka-url localhost:9092

```

As you can see both of the subcommands receive the kafka url and then you will have to go into the details depending on the subcommand passed e.g. `python3 src/webcheck.py producer -h`.

After you have finished the development, you can use `make down` for shutting down all the containers running in background.

## DB Schema

There are two tables: webpage and webcheck

webpage:
  - id
  - url

webcheck:
  - id
  - webpage\_id
  - response\_time
  - content\_check (optional)
  - queried\_at

webpage stores the url that are checked. And webcheck stores the check done and its details.

## TODOS and improvements

There are some improvements and TODOs that were detected during the development.

* A more detailed information about time measurement would be using the tracing feature that is part of the aiohttp module. You can discriminate time for headers, dns query, redirection, content among others.
* Better error handling
* Unhardcode group_id and topic
* Development config (kafka, db config, etc) in a single place
* Split consumer and producer module
* Gracefully shutdown
* Better logging
* Finish the docker image for distribution and deploymnent
* Test cases for WebCheckConsumer
* Integration test (producer and consumer running for some time) and then put it in a CI.
