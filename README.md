Blendqueue
==========
This tool is divided in two programs. `blenderenqueue.py` moves a blender file to the central fileserver and adds the
file to the [rabbitmq][rmq] queue for rendering. On each render node you start `blenderworker.py` and it receives one
task from the rabbitmq server and renders it using [blender].

Requirements
------------
This program assumes that:
- Blender is installed on the render node
- The enqueue and worker tool have access to shared storage
- The enqueue and worker tool have access to a [rabbitmq][rmq] server

Installation
------------
Enqueue node:

```bash
$ git clone https://github.com/MartijnBraam/blendqueue.git
$ pip install pika
```

Rabbit server:

```bash
$ apt get install rabbitmq
```

Worker node:

```bash
$ apt-get install blender
$ pip install pika
$ git clone https://github.com/MartijnBraam/blendqueue.git
```

Configuration
-------------
Both tools read their config from blenderqueue.cfg in the current directory by default. Override this with the
--configfile= parameter

Example blenderqueue.cfg:

```ini
[rabbitmq]
server=127.0.0.1
username=guest
password=guest
port=5672
virtualhost=%%2f #this is an config-escaped urlencoded /

[storage]
path=/mnt/storage/rabbit/blender
```

Usage
-----
Start the worker script on a worker node.

```bash
$ python3 blenderworker.py
or
$ python3 blenderworker.py --configfile=/etc/blenderqueue.cfg
```

Enqueue an blend file.

```bash
$ python blenderenqueue.py --start 1 --end 250 testrender test.blend
```

This will copy test.blend to the fileserver configured in the config file and add 250 tasks to the queue (one per frame).
rabbitmq will now dispatch the tasks to all started blenderworkers.

  [rmq]: http://rabbitmq.org
  [blender]: http://blender.org
