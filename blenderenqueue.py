import pika
import json
import configparser
import argparse

parser = argparse.ArgumentParser(description="Tool to put tasks in the rabbitmq queue for blender-queue")
parser.add_argument('-c', '--configfile', help="Set config file to use", default="blenderqueue.cfg", type=open)
parser.add_argument('-f', '--frame', help="Set frame number to render", default=1, type=int)
parser.add_argument('-s', '--start', help="Set first frame to render", type=int)
parser.add_argument('-e', '--end', help="Set last frame to render", type=int)
parser.add_argument('-F', '--format', help="Set blender output format", default="PNG")
parser.add_argument('name', help="Name for new job")
parser.add_argument('file', help="File to move to storage server")
args = parser.parse_args()

startFrame = 0
endFrame = 0
if args.start != None or args.end != None:
    if args.frame != 1:
        print("Dont define --frame when using --start and --end")
        exit(1)
    if args.start == None or args.end == None:
        print("Specify both --start and --end")
        exit(1)
    startFrame = args.start
    endFrame = args.end
else:
    startFrame = args.frame
    endFrame = args.frame

config = configparser.ConfigParser()
config.read_file(args.configfile)

rabbitmqUrl = "amqp://{config[user]}:{config[pass]}@{config[host]}:{config[port]}/{config[vhost]}".format(config={
            'user': config['rabbitmq']['username'],
            'pass': config['rabbitmq']['password'],
            'host': config['rabbitmq']['server'],
            'port': config['rabbitmq']['port'],
            'vhost': config['rabbitmq']['virtualhost']
        })

connection = pika.BlockingConnection(pika.URLParameters(rabbitmqUrl))
channel = connection.channel()
channel.queue_declare(queue='render', durable=True)

for frame in range(startFrame, endFrame + 1):
    task = {
        'taskId': args.name,
        'frame': frame,
        'format': args.format
    }
    queueMessage = json.dumps(task)
    channel.basic_publish(exchange='',
                          routing_key='render',
                          body=queueMessage,
                          properties=pika.BasicProperties(
                              delivery_mode=2,  # make message persistent
                          ))

print("Added {} frames to the queue".format(len(range(startFrame, endFrame + 1))))
connection.close()
