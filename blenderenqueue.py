import pika
import json
import configparser
import argparse
import shutil
import os


# Parse arguments
parser = argparse.ArgumentParser(description="Tool to put tasks in the rabbitmq queue for blender-queue")
parser.add_argument('-c', '--configfile', help="Set config file to use", default="blenderqueue.cfg", type=open)
parser.add_argument('-f', '--frame', help="Set frame number to render", default=1, type=int)
parser.add_argument('-s', '--start', help="Set first frame to render", type=int)
parser.add_argument('-e', '--end', help="Set last frame to render", type=int)
parser.add_argument('-F', '--format', help="Set blender output format", default="PNG")
parser.add_argument('name', help="Name for new job")
parser.add_argument('file', help="File to move to storage server")
args = parser.parse_args()

# Parse --frame or --start and --end into a frame range
startFrame = 0
endFrame = 0
if args.start != None or args.end != None: # User has specified start or end frames
    if args.frame != 1: # User has specified both --frame and --start or --end
        print("Dont define --frame when using --start and --end")
        exit(1)
    if args.start == None or args.end == None: # User forgot to specify start or end
        print("Specify both --start and --end")
        exit(1)

    # Save range to variable
    startFrame = args.start
    endFrame = args.end
else:
    # User has specified only --frame, create range with one frame
    startFrame = args.frame
    endFrame = args.frame

# Read the config file
config = configparser.ConfigParser()
config.read_file(args.configfile)

# Generate connectionstring for pika to connect to the rabbitmq server
rabbitmqUrl = "amqp://{config[user]}:{config[pass]}@{config[host]}:{config[port]}/{config[vhost]}".format(config={
            'user': config['rabbitmq']['username'],
            'pass': config['rabbitmq']['password'],
            'host': config['rabbitmq']['server'],
            'port': config['rabbitmq']['port'],
            'vhost': config['rabbitmq']['virtualhost']
        })

# Create pika connection instance
connection = pika.BlockingConnection(pika.URLParameters(rabbitmqUrl))
channel = connection.channel()

# Declare render queue if it don't exist yet
channel.queue_declare(queue='render', durable=True)

# Create a new directory on the fileserver with the task name
os.mkdir(os.path.normpath(config["storage"]["path"] + "/" + args.name))

# Copy the blend file to the fileserver
shutil.copy(args.file, os.path.normpath(config["storage"]["path"] + "/" + args.name + "/input.blend"))

# Loop through the frames defined by the arguments
for frame in range(startFrame, endFrame + 1):

    # Create a task object for the current frame
    task = {
        'taskId': args.name,
        'frame': frame,
        'format': args.format
    }

    # Convert the message to json (rabbitmq only supports binairy blobs)
    queueMessage = json.dumps(task)

    # Send the queueMessage to rabbitmq in the render queue
    channel.basic_publish(exchange='',
                          routing_key='render',
                          body=queueMessage,
                          properties=pika.BasicProperties(
                              delivery_mode=2,  # make message persistent
                          ))

print("Added {} frames to the queue".format(len(range(startFrame, endFrame + 1))))
connection.close()
