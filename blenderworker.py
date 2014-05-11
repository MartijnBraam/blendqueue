import subprocess
import json
import pika
import configparser
import argparse
import os


class BlenderWorker:

    def __init__(self):
        # Parse arguments
        parser = argparse.ArgumentParser(description="Tool to render blender-queue tasks")
        parser.add_argument('-c', '--configfile', help="Set config file to use", default="blenderqueue.cfg", type=open)
        args = parser.parse_args()

        # Parse configfile
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
        self.config = config
        self.current_task = None

        # Create pika connection instance
        self.connection = pika.BlockingConnection(pika.URLParameters(rabbitmqUrl))
        self.channel = self.connection.channel()

        # Declare queues if they don't exist yet
        self.channel.queue_declare(queue='render', durable=True)
        self.channel.queue_declare(queue='progress', durable=True)
        self.channel.queue_declare(queue='postprocess', durable=True)

        # Make sure we only one task assigned at a time
        self.channel.basic_qos(prefetch_count=1)

        # Register handler for incoming message on render queue
        self.channel.basic_consume(self.render, queue='render')

        # Block and wait for messages
        print('Waiting for tasks in rabbitmq render queue.')
        self.channel.start_consuming()

    def send(self, queue, message):
        self.channel.basic_publish(exchange='',
                                   routing_key=queue,
                                   body=json.dumps(message))

    def render(self, ch, method, properties, task):
        task = json.loads(task.decode())
        self.current_task = task

        print('Received task {id}, frame {frame}, format {format}'.format(
            id=task["taskId"],
            frame=task["frame"],
            format=task["format"]))

        # Create command line for blender based on information in config file and received task
        blender_task = [
            "blender",
            "-b", os.path.normpath(self.config["storage"]["path"] + "/" + str(task['taskId']) + "/input.blend"),
            "-o", "//frame",
            "-F", str(task['format']),
            "-x", "1",
            "-f", str(task['frame'])
        ]

        # Print commando to be run
        print("Starting " + " ".join(blender_task))

        # Start blender process and connect pipes to standard input and output
        blender_process = subprocess.Popen(blender_task,
                                           stdin=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           stdout=subprocess.PIPE)

        # Loop until break is called
        while True:

            # Receive one line from the stdout pipe from blender
            line = blender_process.stdout.readline().decode()

            # Check if process is running
            if line == '' and blender_process.poll() != None:
                # End the while loop
                break

            # Print blender output
            print("    " + line.strip())

            # Add blender output to progress queue (Used in webinterface)
            self.send('progress', {
                'task': task,
                'line': line
            })

            # Check for save message with filename
            if line[0:6] == "Saved:":
                filename = line.split(' ')[1]

                # Remove storage path from filename as this is node specific
                filename = filename.replace(self.config["storage"]["path"], "")

                # Send the filename and task info to the postprocess queue
                self.send("postprocess", {
                    'task': task,
                    'file': filename
                })
                print("Queued postprocess task for {}".format(filename))

        # ACK message in rabbitMQ queue to mark it as completed
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print('Completed task {id}, frame {frame}, format {format}'.format(id=task["taskId"],
                                                                           frame=task["frame"],
                                                                           format=task["format"]))
        print('Waiting for next task in rabbitmq render queue.')

if __name__ == "__main__":
    worker = BlenderWorker()