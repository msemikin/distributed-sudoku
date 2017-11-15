from collections import defaultdict
from server.sudoku import Sudoku
from common.protocol import *
import threading
import uuid

import logging

logger = logging.getLogger(__name__)


class Room(object):
    def __init__(self, name, max_users, logger):
        """
        creates new game
        """
        self.id = str(uuid.uuid1())
        self._logger = logger
        self._logger.info("Room \"%s\" created" % (name))
        self.lock = threading.Lock()
        self.name = name
        self.users = []
        self.scores = {}
        self.max_users = max_users
        self.game_started = False
        self.__sudoku = Sudoku(0.02)
        self.__scores = defaultdict(lambda: 0)

    def full(self):
        """
        checks if the game has all the users it needs
        """
        return len(self.users) == self.max_users

    def add_client(self, client):
        """
        adds new user to the game
        """
        self.lock.acquire()
        if self.full():
            self.lock.release()
            raise Exception
        self.users.append(client)
        if len(self.users) == self.max_users:
            self.game_started = True
            self.__send_notification(START_GAME, matrix=str(self.__sudoku.print_matrix()))
        else:
            self.__people_changed_notification(ignore=client)
        self.lock.release()

    def remove_client(self, client):
        """
        deletes user from the game
        """
        self.lock.acquire()
        self.users.remove(client)
        self.__people_changed_notification()
        if len(self.users) == 1:
            self.__send_notification(SUDOKU_SOLVED, scores=self.__scores)
        self.lock.release()

    def set_value(self, name, x, y, value, prev, **kargs):
        self.lock.acquire()

        if self.__sudoku.unsolved[x][y] != prev:
            self.lock.release()
            return False
        if self.__sudoku.check(x, y, value):
            self.__scores[name] += 1
        else:
            self.__scores[name] -= 1
        self.__sudoku.unsolved[x][y] = value
        self.__send_notification(SUDOKU_CHANGED, x=x, y=y, value=value, ignore=self)

        solved = True
        for i in range(9):
            for j in range(9):
                if self.__sudoku.unsolved[i][j] != self.__sudoku.solved[i][j]:
                    solved = False
            if not solved:
                break
        if solved:
            self.__send_notification(SUDOKU_SOLVED, scores=self.__scores)
        self.lock.release()
        return True

    def get_score(self):
        """
        returns list of users' scores
        """
        return self.scores

    def __people_changed_notification(self, ignore=None):
        """
        creates notification if list of users in a game changes
        """
        names = []
        for user in self.users:
            names.append(user.name)
        self.__send_notification(PEOPLE_CHANGED, users=names, room_name=self.name, max_users=self.max_users, need_users=(self.max_users - len(names)), ignore=ignore)

    def __send_notification(self, type, ignore=None, **kargs):
        """
        sends given notification
        """
        for user in self.users:
            if user == ignore:
                continue
            user.send_notification(type, **kargs)
