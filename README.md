Invocation

python3 webchecker.py --kafka-url http://localhost:8500 --url https://theip.me --regex-check 'Connection details'

make a sha1 hash for each url and if there is no an entry in the table, add a
new one.

Schema

Two tables: webpage and webcheck

webpage:
  - id
  - sha1
  - url

webcheck:
  - id
  - webpage\_id
  - response\_time
  - content\_check (optional)

Improvements

* A more detailed information about time measurement would be using the tracing feature that is part of the aiohttp module. You can discriminate time for headers, dns query, redirection, content among others.
* Better error handling
* Gracefully shutdown
* Unhardcode group_id and topic
