#!/usr/bin/env python
# coding: utf-8

import pygtk
pygtk.require('2.0')
import gtk
import sys
import os
import subprocess
import re
import json
import time, argparse

import tic_tac_common as ttc

class TicTacToeGame(gtk.Builder):

	def __init__ (self):
		"""
		Init GUI
		Connect to the server
		"""

		super(TicTacToeGame, self).__init__()

		self.add_from_file(os.path.join(os.path.dirname(__file__), "tic-tac-client-gui.glade"))
		self.connect_signals(self)

		# connect cell's event with signal handler and coordinates data
		self.cell11.connect("toggled", self.on_cell_toggled, "0 0")
		self.cell12.connect("toggled", self.on_cell_toggled, "0 1")
		self.cell13.connect("toggled", self.on_cell_toggled, "0 2")

		self.cell21.connect("toggled", self.on_cell_toggled, "1 0")
		self.cell22.connect("toggled", self.on_cell_toggled, "1 1")
		self.cell23.connect("toggled", self.on_cell_toggled, "1 2")

		self.cell31.connect("toggled", self.on_cell_toggled, "2 0")
		self.cell32.connect("toggled", self.on_cell_toggled, "2 1")
		self.cell33.connect("toggled", self.on_cell_toggled, "2 2")

		#self.TicTacToeWindow.connect("delete-event", self.on_window1_delete_event)
		self.TicTacToeWindow.show_all()

		# accept global or command line arg value
		# ttc.DEBUG = 1

		self.s = self._get_client_socket()




#-----------------------------------------------------------------------------#

	def __getattr__(self, attr):
		"""
		reference to widgets from @glade-file by their id
		"""

		obj = self.get_object(attr)
		if not obj:
			raise AttributeError('object %r has no attribute %r' % (self, attr))
		setattr(self, attr, obj)
		return obj

# --------------------------------------------------------------------------- #


	def _get_client_socket (self):
		"""
		return client socket connected to the server. fail if error with msg
		"""

		self.statusbar.push(0, "Connecting to the server...")

		try:
			s = ttc.get_client_socket(exception=True)
			self.statusbar.push(0, "Connected")

			greeting = ttc.get_msg_from_socket(s)
			ttc.d(greeting)

		except Exception as exp:
			ttc.d("1 {}".format(exp))
			self.show_error_dialog(str(exp))
			sys.exit(1)

		return s


# --------------------------------------------------------------------------- #

	def _get_msg_from_server_socket (self):
		""" Function doc """

		try:
			print("Blocked: wait for msg from server...")
			msg = ttc.get_msg_from_socket(self.s)
			return msg

		except Exception as exp:
			ttc.d("2: {}".format(exp))
			self.show_error_dialog(str(exp))
			self.on_TicTacToeWindow_delete_event(self.TicTacToeWindow, "delete-event")


# --------------------------------------------------------------------------- #

	def show_error_dialog (self, msg=""):
		"""
		"""
		msg_d = gtk.MessageDialog(self.TicTacToeWindow
					, gtk.DIALOG_MODAL
					, gtk.MESSAGE_ERROR
					, gtk.BUTTONS_OK
					, msg
					)
		msg_d.run()
		msg_d.destroy()

# --------------------------------------------------------------------------- #

	def show_info_dialog (self, msg=""):
		"""
		"""
		msg_d = gtk.MessageDialog(self.TicTacToeWindow
					, gtk.DIALOG_MODAL
					, gtk.MESSAGE_INFO
					, gtk.BUTTONS_OK
					, msg
					)
		msg_d.run()
		msg_d.destroy()

# --------------------------------------------------------------------------- #

	def handle_server_answer (self, msg):
		"""check for error and winner variables,
		if non zero - show dialog and exit

		@param
			msg: json-string from server
		"""

		ttc.d("handle server answer: {}".format(msg))

		try:
			tmp_dict = json.loads(msg)

			winner = tmp_dict["winner"]
			error  = tmp_dict["error"]	# suppose, we can't get an error from server

			if error:
				error_text = "smth bad happend"
				ttc.d(error_text)
				self.show_error_dialog(error_text)
				sys.exit(1)


			if 0 == winner :
				pass
			else:
				winner_text = {
					1: "Sorry, but you are a loser... =\\",
					2: "You win!",
					3: "Friendship wins! (tie)"
				}.get(winner, "wtf")

				self.show_info_dialog(winner_text)
				sys.exit(0)

		except Exception as exp:
			# should not happend
			ttc.d("3 {}".format(exp))
			self.show_error_dialog(str(exp))
			self.on_TicTacToeWindow_delete_event(self.TicTacToeWindow, "delete-event")

# --------------------------------------------------------------------------- #
# --------------------------- events handelers ------------------------------
# --------------------------------------------------------------------------- #

	def on_TicTacToeWindow_delete_event(self, window, event):
		"""
		Close button press handler
		"""

		ttc.d("Close button pressed")
		self.s.close()

		gtk.main_quit()

# --------------------------------------------------------------------------- #
# main game login is here
# --------------------------------------------------------------------------- #

	def on_cell_toggled (self, button, data=None):
		"""
		Toogle button
		Lock it, to prevent unpress,
		"""

		# lock UI
		self.TicTacToeWindow.set_sensitive(False)
		self.statusbar.push(0, "Pressed btn with coords: {}".format(data))


		# lock cell
		button.set_sensitive(False)
		button.set_active(True)


		# apply user turn
		button.set_label(ttc.USER_STEP)


		# create correct json-turn
		### suppose, developer is True man,
		### and all data is correct here.)
		user_turn_json = self.convert_str_to_json_dict_step(data)


		# send turn to the server
		self.s.sendall(user_turn_json)


		# get answer
		self.statusbar.push(0, "Waiting for server validation...")
		res = self._get_msg_from_server_socket()
		time.sleep(0.1)


		# check for errors and winners in the answer
		# if winner - show msg and exit after that
		self.handle_server_answer(res)


		# get server's turn
		self.statusbar.push(0, "Waiting for server's turn...")
		server_turn_json = self._get_msg_from_server_socket()


		# apply server's turn
		self.apply_server_turn(server_turn_json)


		# check for winners or TIE
		# exit with msg if a winner exists
		self.handle_server_answer(server_turn_json)

		# unlock UI
		self.TicTacToeWindow.set_sensitive(True)
		self.statusbar.push(0, "Your turn")

		# exit handler and wait for user turn
		return;


# --------------------------------------------------------------------------- #

	def apply_server_turn(self, server_turn_json):
		""" Function doc """

		ttc.d("apply server turn: {}".format(server_turn_json))
		try:
			tmp_dict = json.loads(server_turn_json)
			row = tmp_dict["step"][0]
			col = tmp_dict["step"][1]

			# server sends coordinates - indexes (from 0,0)
			# but buttons in the gui named from 1,1
			# so, plus one.
			cell_name = "cell" + str(row + 1) + str(col + 1)
			ttc.d("apply server step, try to access : {}".format(cell_name))

			cell = self.get_object(cell_name)
			cell.set_sensitive(False)
			cell.set_label(ttc.SERVER_STEP)

		except Exception as exp:
			ttc.d(exp)
			self.show_error_dialog(str(exp))
			sys.exit(1)

# --------------------------------------------------------------------------- #

	def convert_str_to_json_dict_step (self, data):
		"""
		"""
		ttc.d("convert input: {}".format(data))

		parts = re.split("\s*", data)
		row = int(float(parts[0]))
		col = int(float(parts[1]))

		answer = {}
		answer["step"] = [row, col]
		turn_json = json.dumps(answer)

		ttc.d("convert result: {}".format(turn_json))

		return turn_json
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #


if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Run a GUI client for Tic-Tac-toe client-server game.')

	parser.add_argument('--host',       help='specify host/ip, where server is running')
	parser.add_argument('-p', '--port', help='specify a port to connect to',
						type=int)
	parser.add_argument('--debug', help='show debug output', action='store_true')

	args = parser.parse_args()

	if args.debug:
		ttc.DEBUG = 1
		print("Debug output: On")

	if args.host is not None:
		ttc.SERVER_IP = args.host
	if args.port is not None:
		ttc.SERVER_PORT = args.port


	ticTacToeGame = TicTacToeGame()
	gtk.main()
