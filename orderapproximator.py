from re import search as re_search, \
               sub as re_sub, \
               match as re_match
from time import sleep as time_sleep
from threading import Thread as threading_Thread
from difflib import SequenceMatcher as difflib_SequenceMatcher

from kalliope.core import SignalModule, MissingParameter
from kalliope.core.NotificationManager import NotificationManager
from kalliope.core.OrderAnalyser import OrderAnalyser
from kalliope.core import Utils

import logging
logging.basicConfig()
logger = logging.getLogger("kalliope")


class OrderVariable(str):
	pass


class Orderapproximator(SignalModule, NotificationManager, threading_Thread):
	def __init__(self, **kwargs):
		SignalModule.__init__(self, **kwargs)
		NotificationManager.__init__(self)
		threading_Thread.__init__(self, name=Orderapproximator)
		Orderapproximator.instance = self
		self.OrderAnalyser_get_list_match_synapse = OrderAnalyser.get_list_match_synapse
		OrderAnalyser.get_list_match_synapse = Orderapproximator.get_list_match_synapse

		self.const_order_minimum_sentence_similarity = 0.8
		self.variadic_order_minimum_word_similarity = 0.5


	def run(self):
		Utils.print_info('[Orderapproximator] Starting thread')
		while True:
			time_sleep(1)
		Utils.print_info('[Orderapproximator] Ending thread')


	def patch_variadic_order_const_words(self, synapse_order_tuple):
		user_order = synapse_order_tuple.user_order.lower()
		signal_order = synapse_order_tuple.matched_order.lower()
		user_order_words = user_order.split()
		signal_order_words = re_sub(r'{{\s*(\w+)\s*}}', r'{{\1}}', signal_order).split()
		for i in range(0, len(signal_order_words)):
			if re_match(r'{{\w+}}', signal_order_words[i]) is not None:
				signal_order_words[i] = OrderVariable(signal_order_words[i])
		sequence_matcher = difflib_SequenceMatcher(None, user_order_words, signal_order_words)
		matches = sequence_matcher.get_matching_blocks()
		matches.pop()
		user2signal_word_matches = [False] * len(user_order_words)
		for match in matches:
			for user2signal_offset in range(match.a, match.a+match.size):
				user2signal_word_matches[user2signal_offset] = user2signal_offset + (match.b-match.a)
		for user2signal_offset in range(0, len(user2signal_word_matches)):
			if user2signal_word_matches[user2signal_offset] is False:
				if user2signal_offset > 0 and user2signal_offset < len(user2signal_word_matches)-1:
					if (user2signal_word_matches[user2signal_offset+1]-user2signal_word_matches[user2signal_offset-1]) == 2:
						signal_word_offset = user2signal_word_matches[user2signal_offset-1] + 1
						signal_word_pre = signal_order_words[signal_word_offset-1]
						signal_word_post = signal_order_words[signal_word_offset+1]
						if isinstance(signal_word_pre, OrderVariable) is False and isinstance(signal_word_post, OrderVariable) is False:
							if isinstance(signal_order_words[signal_word_offset], OrderVariable) is False:
								word_user = user_order_words[user2signal_offset]
								word_signal = signal_order_words[signal_word_offset]
								word_score = difflib_SequenceMatcher(None, word_user, word_signal).ratio()
								if word_score >= self.variadic_order_minimum_word_similarity:
									user_order_words[user2signal_offset] = signal_order_words[signal_word_offset]
				elif user2signal_offset == 0 and len(user2signal_word_matches) > 1:
					if user2signal_word_matches[1] is not False:
						signal_word_offset = user2signal_word_matches[1]
						if isinstance(signal_order_words[signal_word_offset], OrderVariable) is False:
							word_score = difflib_SequenceMatcher(None, user_order_words[0], signal_order_words[signal_word_offset-1]).ratio()
							if word_score >= self.variadic_order_minimum_word_similarity:
								user_order_words[0] = signal_order_words[signal_word_offset-1]
				elif user2signal_offset == len(user2signal_word_matches)-1 and len(user2signal_word_matches) > 1:
					if user2signal_word_matches[-2] is not False:
						signal_word_offset = user2signal_word_matches[-2]
						if isinstance(signal_order_words[signal_word_offset], OrderVariable) is False:
							word_score = difflib_SequenceMatcher(None, user_order_words[-1], signal_order_words[signal_word_offset+1]).ratio()
							if word_score >= self.variadic_order_minimum_word_similarity:
								user_order_words[-1] = signal_order_words[signal_word_offset+1]
		patched_user_order = ' '.join(user_order_words)
		if user_order != patched_user_order:
			logger.debug(f"[signal:orderapproximator] patched const words in variadic user order: '{user_order}' => '{patched_user_order}'")
			synapse_order_tuple = synapse_order_tuple._replace(user_order=patched_user_order)
		return synapse_order_tuple


	def evaluate_variadic_order_variables(self, synapse_order_tuple):
		user_order = synapse_order_tuple.user_order.lower()
		signal_order = synapse_order_tuple.matched_order.lower()
		user_order_words = user_order.split()
		signal_order_words = re_sub(r'{{\s*(\w+)\s*}}', r'{{\1}}', signal_order).split()
		for i in range(0, len(signal_order_words)):
			if re_match(r'\{\{\w+\}\}', signal_order_words[i]) is not None:
				signal_order_words[i] = OrderVariable(signal_order_words[i])
		sequence_matcher = difflib_SequenceMatcher(None, user_order_words, signal_order_words)
		matches = sequence_matcher.get_matching_blocks()
		matches.pop()
		signal2user_word_matches = [False] * len(signal_order_words)
		for match in matches:
			for signal2user_offset in range(match.b, match.b+match.size):
				signal2user_word_matches[signal2user_offset] = signal2user_offset + (match.a-match.b)
		for signal2user_offset in range(0, len(signal2user_word_matches)):
			if signal2user_word_matches[signal2user_offset] is False:
				if isinstance(signal_order_words[signal2user_offset], OrderVariable) is False:
					logger.debug(f"variadic order '{signal_order}' + {signal2user_word_matches} => '{user_order}' fails at word " \
					             f"{signal2user_offset} ('{signal_order_words[signal2user_offset]}')")
					return False
		return True


	def match_variadic_order_synapses(self, user_order: str, synapse_order_tuples: list) -> list:
		list_order_matches = []
		for synapse_order_tuple in synapse_order_tuples:
			if re_search(r'{{\s*\w+\s*}}', synapse_order_tuple.matched_order) is not None:
				logger.debug(f"[signal:orderapproximator] patching variadic order: {synapse_order_tuple.user_order}")
				patched_synapse_order_tuple = self.patch_variadic_order_const_words(synapse_order_tuple)
				logger.debug(f"[signal:orderapproximator] patched variadic order: {patched_synapse_order_tuple.user_order}")
				if patched_synapse_order_tuple is not None:
					logger.debug(f"[signal:orderapproximator] evaluating variables for variadic order: {patched_synapse_order_tuple.user_order}")
					if self.evaluate_variadic_order_variables(patched_synapse_order_tuple) is True:
						logger.info(f"[signal:orderapproximator] Matched (variadic) user order '{synapse_order_tuple.user_order}' to " \
						    f"'{patched_synapse_order_tuple.matched_order}' (word similarity>={self.variadic_order_minimum_word_similarity:.2f})")
						list_order_matches.append(patched_synapse_order_tuple)
		return list_order_matches


	def match_const_order_synapses(self, user_order: str, synapse_order_tuples: list) -> list:
		list_approximately_matching_synapses = []
		dict_synapse_scores = {}
		for synapse_order_tuple in synapse_order_tuples:
			synapse_score = difflib_SequenceMatcher(None, synapse_order_tuple.user_order, synapse_order_tuple.matched_order).ratio()
			if synapse_score not in dict_synapse_scores:
				dict_synapse_scores[synapse_score] = []
			dict_synapse_scores[synapse_score].append(synapse_order_tuple)
		for synapse_score in [score for score in sorted(dict_synapse_scores.keys(), reverse=True) if score >= self.const_order_minimum_sentence_similarity]:
			for synapse_tuple in dict_synapse_scores[synapse_score]:
				if re_search(r'{{\s*\w+\s*}}', synapse_tuple.matched_order) is None:
					logger.info(f"[signal:orderapproximator] Matched user order '{synapse_tuple.user_order}' to '{synapse_tuple.matched_order}' " \
					            f"with similarity score={synapse_score:.2f} (min={self.const_order_minimum_sentence_similarity:.2f})")
					list_approximately_matching_synapses.append(synapse_tuple)
		return list_approximately_matching_synapses


	def get_list_approximately_matching_synapses(self, user_order: str, synapse_order_tuple) -> list:
		synapse_order_tuples = []
		for synapse in [synapse for synapse in OrderAnalyser.brain.synapses if synapse.enabled is True]:
			for signal in [signal for signal in synapse.signals if signal.name == 'order']:
				signal_order = OrderAnalyser.get_signal_order(signal)
				synapse_order_tuples.append(synapse_order_tuple(synapse=synapse, matched_order=signal_order, user_order=user_order))
		list_approximately_matching_synapses = self.match_const_order_synapses(user_order, synapse_order_tuples)
		if len(list_approximately_matching_synapses) == 0:
			logger.debug(f"[signal:orderapproximator] no const order matched with order similarity score>={self.const_order_minimum_sentence_similarity}, " \
			             f"trying variadic matching...")
			list_approximately_matching_synapses = self.match_variadic_order_synapses(user_order, synapse_order_tuples)
		return list_approximately_matching_synapses


	@classmethod
	def get_list_match_synapse(cls, user_order, synapse_order_tuple):
		result = Orderapproximator.instance.OrderAnalyser_get_list_match_synapse(user_order, synapse_order_tuple)
		if len(result) == 0:
			result = Orderapproximator.instance.get_list_approximately_matching_synapses(user_order, synapse_order_tuple)
		return result

