from os.path import exists as os_path_exists
from time import sleep as time_sleep
from threading import Thread as threading_Thread
from paho.mqtt import client as paho_mqtt_client
import logging

from kalliope.core import SignalModule, MissingParameter
from kalliope.core.OrderAnalyser import OrderAnalyser
from kalliope.core.NotificationManager import NotificationManager
from kalliope.core import Utils

logging.basicConfig()
logger = logging.getLogger("kalliope")


class Orderapproximator(SignalModule, NotificationManager, threading_Thread):
	def __init__(self, **kwargs):
		SignalModule.__init__(self, **kwargs)
		NotificationManager.__init__(self)
		threading_Thread.__init__(self, name=Orderapproximator)
		Orderapproximator.singleton = self
		self.OrderAnalyser = object()
		self.OrderAnalyser.get_list_match_synapse = OrderAnalyser.get_list_match_synapse
		OrderAnalyser.get_list_match_synapse = Orderapproximator.get_list_match_synapse


	def run(self):
		Utils.print_info('[Orderapproximator] Starting thread')
		while True:
			time_sleep(1)
		Utils.print_info('[Orderapproximator] Ending thread')


	@classmethod
	def get_list_match_synapse(cls, order, synapse_order_tuple):
		result = self.OrderAnalyser.get_list_match_synapse(order, synapse_order_tuple)
		print(result)
		return result

