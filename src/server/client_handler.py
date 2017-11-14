from common.networking import recv, send
from common.protocol import *
from common.listener import handler
import socket
from collections import defaultdict
from common.networking import request
import uuid

class ClientHandler(object):
    def __init__(self, s, room_manager):
        self.id = id = str(uuid.uuid1())
        self.socket = s
        self.s_to_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.handlers = defaultdict(list)
        self.room_manager = room_manager
        self.room = None
        self.name = "Undefined"
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, 'handled_event'):
                self.handlers[attr.handled_event].append(attr)

    def run(self):
        while True:
            message = recv(self.socket)
            type = message['type']
            for handler in self.handlers[type]:
                handler(message)

    @handler(PRINT_MESSAGE)
    def print_message(self, args):
        print(args['message'])
        self.__send(RESPONSE_OK)


    @handler(CLIENT_START_LISTEN)
    def send_client_port(self, args):
        self.s_to_client.connect((self.socket.getpeername()[0], args["port"]))
        self.__send(RESPONSE_OK)

    @handler(REQUEST_CREATE_ROOM)
    def create_room(self, args):
        room = self.room_manager.create_room(args["name"], args["max_users"])
        room.add_client(self)
        self.room = room
        self.__send(RESPONSE_OK)
        print("room creted %s %d" % (room.name, room.max_users))

    @handler(GET_SCORE)
    def get_score(self):
        self.room.get_score()

    @handler(SET_NAME)
    def set_name(self, args):
        self.name = args["name"]
        self.__send(RESPONSE_OK)

    def send_notification(self, type, **args):
        for handler in self.handlers[type]:
            handler(args)

    @handler(GET_ROOMS)
    def get_available_rooms(self):
        rooms = []
        for room in self.room_manager.get_rooms():
            rooms.append({"name": room.name, "max": room.max_users, "current": len(room.users)})
        self.__send(RESPONSE_OK, rooms = rooms)

    def __request(self, type, **kargs):
        return request(self.s, type=type, **kargs)

    @handler(START_GAME)
    def __start_game(self, **kargs):
        response = request(self.s, type=START_GAME, **kargs)
        # TODO Process error
        if response['type'] != RESPONSE_OK:
            return

    def __send(self, type, **kargs):
        try:
            send(self.socket, type=type, **kargs)
        except:
            LOG.debug("Exception occurs in client %s" % (self.name))
