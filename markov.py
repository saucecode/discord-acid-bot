# markov.py
import os, re, pickle, random

class Markov():
	def __init__(self):
		self.users = {}
		self.users_incomplete = {}
		self.last_speaker = {}
		if os.path.exists('markov.pickle'):
			self.load()
		'''
			Re-written MarkovChain module.

			This is going to be a ground up re-write with some changes specific
			to making the feature more compatible with the Discord environment
			and chat rooms in general.
		'''

	def add_line(self, channelid, userid, words):
		# ignore command lines

		if len(words) > 2 and words.startswith('\\\\'):
			return

		# clean lines
		words = self.holy_cleanse(words)

		if not channelid in self.last_speaker:
			self.last_speaker[channelid] = userid

		# flush the last speaker's buffer if a new speaker is on
		if self.last_speaker[channelid] != userid:
			self.flush_buffer(channelid, self.last_speaker[channelid])
			self.last_speaker[channelid] = userid


		if not channelid in self.users_incomplete:
			self.users_incomplete[channelid] = {} # username: line

		if not userid in self.users_incomplete[channelid]:
			self.users_incomplete[channelid][userid] = []

		self.users_incomplete[channelid][userid].extend(words.split(' '))

	def holy_cleanse(self, words):
		# remove hyperlinks
		# strip whitespace

		words = re.sub(r'^https?:\/\/.*[\r\n]*', '', words, flags=re.MULTILINE)
		# match mentions r'\<\@\!?[0-9]{15,}\>'

		# remove excess whitespace
		words = re.sub(r'\s+', ' ', words).strip()

		return words

	def flush_buffer(self, channelid, userid):
		buf = self.users_incomplete[channelid][userid]
		triples = self.get_triples(buf)
		print('flushing', self.users_incomplete[channelid][userid])

		if not userid in self.users:
			self.users[userid] = {}

		# go through triples and naively push them onto the user database
		for triple in triples:
			key = (triple[0],triple[1])
			if not key in self.users[userid]:
				self.users[userid][key] = [triple[2]]
			else:
				self.users[userid][key].append(triple[2])

		# clear incompleted
		self.users_incomplete[channelid][userid].clear()

	def get_triples(self, words):
		words_split = words
		triples = []

		if len(words) < 2:
			return triples

		for i in range(len(words_split)):
			try:
				tup = (words_split[i], words_split[i+1], words_split[i+2])
				triples.append(tup)
			except:
				return triples
		return triples

	def remove_duplicates(self, seq):
		seen = set()
		seen_add = seen.add
		return [x for x in seq if not (x in seen or seen_add(x))]

	def imitate(self, userid, max_length=20):
		output = []

		key = random.choice(list(self.users[userid].keys()))
		output.extend(key)

		while len(output) < max_length:
			if not key in self.users[userid]: break

			options = self.users[userid][key]
			if len(options) == 0: break

			chosen = random.choice(options)

			key = (key[1], chosen)
			output.append(chosen)

		return ' '.join(output)

	def save(self):
		with open('markov.pickle','wb') as f:
			pickle.dump(self.users, f)

	def load(self):
		with open('markov.pickle','rb') as f:
			self.users = pickle.load(f)

if __name__ == '__main__':
	import sqlite3

	conn = sqlite3.connect('logs.db')
	c = conn.cursor()

	c.execute('SELECT channel,name,message FROM logs WHERE edited=0 AND deleted=0')
	logs = c.fetchall()
	conn.close()

	print('prepared',len(logs),'lines...')

	markov = Markov()
	for item in logs:
		markov.add_line(item[0], item[1], item[2])

	markov.save()
