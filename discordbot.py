import discord
import asyncio
import requests
import random
import sqlite3
import re
import json
import pickle
import os
import time
import threading
import subprocess
import string
from PIL import Image

from functools import reduce

discord.opus.load_opus('libopus.so.0')

from gtts import gTTS
from youtube_dl import YoutubeDL
import youtube_dl
import markovify

import postfix
import dictionarycom as dictionary
from sailortalk import sailor_word
from markov import Markov

client = discord.Client()
sql = sqlite3.connect('logs.db')
sql_c = sql.cursor()

class VoiceWrapper():
	def __init__(self):
		self.voice = None
		self.player = None
		self.is_ready = True
		self.streaming_media = False
		self.lang = 'en-au'
		self.volume = 0.5
		self.queue = []

	def after(self):
		self.is_ready = True

	def after_streaming(self):
		if len(self.queue) > 0: del self.queue[0]
		if len(self.queue) == 0: self.streaming_media = False
		self.after()

	async def play_next(self, channel=None):
		if channel:
			self.current_channel = channel
		else:
			channel = self.current_channel

		query = self.queue[0]
		if type(query) == tuple and query[1] == 'cache':

			messages_to_delete.append({
				'time': time.time() + 10.0,
				'message': await client.send_message(channel, 'Getting audio for: **%s** ' % (query[0]))
			})

			self.player = voice_wrapper.voice.create_ffmpeg_player('downloaded/'+query[0], after=voice_wrapper.after_streaming)
			self.player.volume = voice_wrapper.volume
			self.streaming_media = True
			self.player.start()

			return

		ydl = YoutubeDL( {'outtmpl': 'downloaded/%(title)s-%(id)s.%(ext)s', 'format': 'bestaudio/best', 'default_search': 'ytsearch', 'cachedir':'downloaded', 'nopart':'true'} )

		try:
			entries = ydl.extract_info(query, download=False)
		except youtube_dl.utils.DownloadError as err:
			await client.send_message(channel, 'Failed to download.')
			self.is_ready = True
			del self.queue[0]
			return

		if 'entries' in entries:
			entries = entries['entries']

		if len(entries) == 0:
			await client.send_message(channel, 'Can\'t find anything :L')

		else:
			entry = entries[0] if type(entries) == list else entries
			messages_to_delete.append({
				'time': time.time() + 10.0,
				'message': await client.send_message(channel, 'Getting audio for: **%s** ' % (entry['title']))
			})

			def _download_call(url):
				ydl.download([url])

			t1 = threading.Thread(target=_download_call, args=(entry['webpage_url'],))
			t1.start()

			for i in range(75):
				time.sleep(0.5)
				if not t1.is_alive(): break
				try:
					guess_name = 'downloaded/' + [x for x in os.listdir('downloaded/') if entry['id'] in x][0]
					if os.path.exists( guess_name ):
						if os.stat(guess_name).st_size > 1024 * 1024:
							break
				except IndexError:
					pass

			fname = 'downloaded/' + [x for x in os.listdir('downloaded/') if entry['id'] in x][0]

			self.player = voice_wrapper.voice.create_ffmpeg_player(fname, after=voice_wrapper.after_streaming)
			self.player.volume = voice_wrapper.volume
			self.streaming_media = True
			self.player.start()

class MathRunner():
	def __init__(self):
		self.problems = {
			'addition': self.addition_problem,
			'subtraction': self.subtraction_problem,
			'multiplication': self.multiplication_problem,
			'surd': self.surd_problem
		}

		self.active_channel = None
		self.active = False

		self.scores = {} # username: score
		self.last_score = {} # username: score

		if os.path.exists('mathscores.json'):
			with open('mathscores.json','r') as f:
				self.scores, self.last_score = json.load(f)

	async def pose_question(self, message):
		self.active_channel = message.channel
		self.active = True

		s,ans = self.problems[ random.choice( list(self.problems.keys()) ) ]()
		self.active_answer = ans
		await client.send_message(message.channel, s)

	async def pose_questionset(self, message):
		self.active_channel = message.channel
		self.active = True

		# list of problem_string, ans pairs
		problems = [self.problems[ random.choice( list(self.problems.keys()) ) ]() for x in range(10)]
		self.answerset = [x[1] for x in problems]

		# print question set
		out = '\n'.join([ x[0] for x in problems])
		await client.send_message(message.channel, '```%s```' % out)

	def addition_problem(self):
		a,b = random.randint(10, 120), random.randint(10, 120)
		ans = a + b
		problem_string = '%i + %i =' % (a,b)
		return problem_string, ans

	def subtraction_problem(self):
		a,b = random.randint(-70, 120), random.randint(10, 70)
		ans = a - b
		problem_string = '%i - %i =' % (a,b)
		return problem_string, ans

	def multiplication_problem(self):
		a,b = random.randint(-15,15), random.randint(2,15)
		ans = a * b
		problem_string = '%i * %i =' % (a,b)
		return problem_string, ans

	def surd_problem(self):
		path = random.choice( [0,1] )
		if path == 0:
			ans = random.randint(2,12)
			problem_string = 'sqrt(%i)' % ans**2

			return problem_string, ans

		elif path == 1:
			n = random.randint(2,16)
			under_root = random.randint(2,16)
			problem_string = '%isqrt(%i)' % (n,under_root**2)
			ans = n * under_root

			return problem_string, ans

		# TODO : add a composite surd problem

	async def answer_query(self, message):
		if not self.active: return
		if not message.channel == self.active_channel: return

		submitted_answers = [ int(x) for x in message.content.split(' ')[1:] ]

		if not len(self.answerset) == len(submitted_answers):
			await client.send_message(message.channel, 'Incomplete number of answers. Reenter them again.')

		correct_answers = len( [x for x,y in zip(self.answerset, submitted_answers) if x == y] )

		if not message.author.name in self.scores:
			self.scores[message.author.name] = 0

		self.scores[message.author.name] += correct_answers
		self.last_score[message.author.name] = correct_answers

		await client.send_message(message.channel, 'You got: %i/%i' % (correct_answers, len(self.answerset)) )

		self.active = False

	async def showscores(self, message):
		with open('mathscores.json','w') as f:
			json.dump([self.scores, self.last_score], f)

		await client.send_message(message.channel, ', '.join( ['%s (%i)' % (x, self.scores[x]) for x in list(self.scores.keys())] ))


markov = Markov()
voice_wrapper = VoiceWrapper()
mathgame = MathRunner()

votes = []

reactions = {}
if os.path.exists('reactions.json'):
	with open('reactions.json','r') as f:
		reactions = json.load(f)

tells = {}
if os.path.exists('tells.json'):
	with open('tells.json','r') as f:
		tells = json.load(f)

playlists = {}
if os.path.exists('playlists.json'):
	with open('playlists.json','r') as f:
		playlists = json.load(f)

reminders = []
if os.path.exists('reminders.json'):
	with open('reminders.json','r') as f:
		reminders = json.load(f)

def save_tells():
	with open('tells.json','w') as f:
		json.dump(tells, f)

def save_reminders():
	with open('reminders.json','w') as f:
		json.dump(reminders, f)

def save_playlists():
	with open('playlists.json','w') as f:
		json.dump(playlists, f)

messages_to_delete = []

remove_urls = lambda x:re.sub(r'^https?:\/\/.*[\r\n]*', '', x, flags=re.MULTILINE)

HELP_STRINGS = {
	'general': r'''```Acid-Bot Help Menu
You are viewing the general help section. Try
\help reactions       \help music       \help imitate
  for more help pages.

The commands are:
\help                This helpful message.
\rr [subreddit]      Get a random image from [subreddit]
\calc [query]        Postfix calculator
\whoami              User stats
\whois [username]    ^ Ditto
\ping                Pong.
\define [word]       Lookup the definition of [word]
\ud [word]           Lookup the urban definition of [word]
\50/50               You feeling lucky?
\flip                Flip a coin
\callvote [message]  Calls a vote and counts the tally after 7 seconds.
\tell @[name] [msg]  Send [msg] to @[name] next time the bot sees them.

\remind @[name] [msg] in [time]    Send a reminder to @[name] after [time].

\listadd [name] [item] Add an item to the list with [name]
\listpop [name] [num]  Remove item [num] from list [name]
\lists                 View your lists
\list [name]           View the contents of list [name]

MathGame Commands
\scores                List math scores
\problems              Start a short 10 question basic facts test
\ans [ans1] [ans2] ... Answer the basic facts test

Debug (Admin) Commands:
\rename [newname] \setgame [playing]
```''',

	'reactions': r'''```Reactions Help Guide
Reactions are a useful way to save images or text to be recalled later.

\reactionadd [name] [url]    Add a new link to the [name] collection
\reactions                   Lists all the reaction collections
\\[name]                     Sends a random reaction from [name] collection (TWO backslashes)

\reactiondel [name] [num]    Delete a reaction with number [num] from collection [name]
```''',

	'imitate': r'''```Imitation commands
The markov bot imitation commands (currently non-functional).

\imitate [username] (length) (tts)  Imitate [username] (Markov Chains!).
\markovusers         List users' markov ratings (higher number means better \imitate)
\markovsave          Save markov data to disk

\markovload \markovclear [username] \markovfeed [username] [url]
```''',

	'music': r'''```Music/Voice Commands
\voice               Connect/disconnect from your voice channel
\play [URL or title] Plays the audio at [URL] or searches YouTube for [Title].
                     Supports playing from 1039 websites (http://bit.ly/2d9yknp)
					 If already playing, adds query to the queue.
\clay [query]        Play/queue a song from the cache.

\clay is *always* faster than \play since it doesn't have to run a search.

\skip                Skip current song.
\queue               View the current queue.
\queuepop [n]        Removes item [n] from the queue.
\stop                Stop playback. Discards queue.

Playlist Commands
\pls                   Display a list of all playlists.
\pl [name]             Displays the songs in a playlist [name].
\pladd [name] [query]  Adds a song (from the cache) into the playlist [name].
\plpop [name] [num]    Removes song number [num] from a playlist [name].
\plplay [name]         Puts the current playlist in the queue.

Google's TTS
\tts [something]     Say [something] with the tts
\chlang              Changes the tts language (from https://pastebin.com/QxdGXShe)
```'''
}

HELP_STRING = r'''Acid-Bot Commands```
\help                This helpful message.
\rr [subreddit]      Get a random image from [subreddit]
\calc [query]        Postfix calculator
\whoami              User stats
\whois [username]    ^ Ditto
\ping                Pong.
\define [word]       Lookup the definition of [word]
\ud [word]           Lookup the urban definition of [word]
\50/50               You feeling lucky?
\flip                Flip a coin
\callvote [message]  Calls a vote and counts the tally after 7 seconds.
\tell @[name] [msg]  Send [msg] to @[name] next time the bot sees them.

\remind @[name] [msg] in [time]    Send a reminder to @[name] after [time].

\imitate [username] (length) (tts)  Imitate [username] (Markov Chains!).
\markovusers         List users' markov ratings (higher number means better \imitate)
\markovsave          Save markov data to disk

\reactionadd [name] [url]  Add a new link to the [name] collection
\reactions                 Lists all the reaction collections
\\[name]                   Random link from [name] collection (TWO backslashes)

\voice               Connect/disconnect from your voice channel
\play [URL or title] Plays the audio at [URL] or searches YouTube for [Title].
                     Supports playing from 1039 websites (http://bit.ly/2d9yknp)
					 If already playing, adds query to the queue.
\clay [query]        Play/queue a song from the cache.
\skip                Skip current song.
\queue               View the current queue.
\queuepop [n]        Removes item [n] from the queue.
\stop                Stop playback. Discards queue.

\tts                 Say something with the tts
\chlang              Changes the tts language (from https://pastebin.com/QxdGXShe)

\scores                List math scores
\problems              Start a short 10 question basic facts test
\ans [ans1] [ans2] ... Answer the basic facts test

Debug (Admin) Commands:
\rename [newname] \setgame [playing] \reactiondel [name] [num] ```'''


async def pong(message):
	await client.send_message(message.channel, '%s pong.' % (message.author.mention))

async def get_random_reddit_image(message):
	subreddit = message.content.split(' ')[1]
	dat = requests.get('https://reddit.com/r/' + subreddit + '/.json', headers={'User-Agent':'Discord-Acid-Bot /u/saucecode'}).json()

	urls = [i['data']['url'] for i in dat['data']['children']] # pull urls from reddit post list
	imgurs = [url for url in urls if any( domain in url for domain in ['imgur.com', 'i.redd.it'] )] # filter links for only these domains

	await client.send_message(message.channel, random.choice(imgurs))

async def get_random_top_reddit_image(message):
	subreddit = message.content.split(' ')[1]
	dat = requests.get('https://reddit.com/r/' + subreddit + '/top/.json?t=all', headers={'User-Agent':'Discord-Acid-Bot /u/saucecode'}).json()

	urls = [i['data']['url'] for i in dat['data']['children']] # pull urls from reddit post list
	imgurs = [url for url in urls if any( domain in url for domain in ['imgur.com', 'i.redd.it'] )] # filter links for only these domains

	await client.send_message(message.channel, random.choice(imgurs))

async def do_postfix_calculation(message):
	await client.send_message(message.channel, postfix.outputResult( postfix.doPostfix(message.content[6:]) ))

async def define_word(message):
	word = message.content.split(' ')[1]
	defs = dictionary.get_definitions(word)[:3]
	if len(defs) == 0:
		await client.send_message(message.channel, 'What even is a %s?' % word)
	else:
		i=1
		out = ''
		for s in defs:
			out += '%i. %s\n' % (i,s)
			i += 1
		await client.send_message(message.channel, '```%s```' % (out,))

async def urban_define_word(message):
	word = message.content[4:]
	definition = dictionary.get_urban_definitions(word)[0]
	for i in range(len(definition['definition'])//2000 + 1):
		await client.send_message(message.channel, '```%s```' % definition['definition'][i*2000:i*2000+2000])
	await client.send_message(message.channel, '```examples: %s```' % definition['example'])

async def whoami(message):
	await whois_user(message.channel, message.author, message.channel.server.id)

async def whois(message):
	target = message.content[7:]
	member = discord.utils.find(lambda m: target.lower() in m.name.lower() or target.lower() in m.display_name.lower(), message.channel.server.members)
	if member:
		await whois_user(message.channel, member)
	else:
		await client.send_message(message.channel, 'I can\'t find a %s' % (target,))

async def whois_user(chan, user, serverid='N/a'):
	await client.send_message(chan, 'Name: %s; Display Name: %s; Discriminator: %s; ID: %s; Server ID %s' % (user.name, user.display_name, user.discriminator, user.id, serverid))

async def do_imitate(message):
	name = message.content.split(' ')[1]
	opts = []
	opts.extend(message.content.split(' ')[2:])

	max_length = 20
	try:
		max_length = int(message.content.split(' ')[2])
	except:
		pass

	if name in markov.users:
		await client.send_message(message.channel, '%s' % (markov.imitate(name, max_length=max_length),), tts='tts' in opts)

async def set_game(message):
	await client.change_presence(game=discord.Game(name=message.content[9:]))

async def rename_bot(message):
	await client.edit_profile(username=message.content.split(' ')[1])
	await client.send_message(message.channel, 'Acknowledged.')

async def markov_save(message):
	markov.save()
	await client.send_message(message.channel, 'Saved markov.json')

async def markov_load(message):
	markov.load()
	await client.send_message(message.channel, 'Loaded markov.json')

async def markov_users(message):
	await client.send_message(message.channel,
		', '.join( ['%s (%i)' % (key, len(markov.users[key])) for key in list(markov.users.keys())] )
	)

async def markov_clear(message):
	target = message.content[13:]
	if target in markov.users:
		del markov.users[target]
		await client.send_message(message.channel, 'Cleared markov data for %s' % (target,))
	else:
		await client.send_message(message.channel, 'Could not find %s in markov.users' % (target,))

async def markov_feed(message):
	username = message.content.split(' ')[1]
	url = message.content.split(' ')[2]
	resp = requests.get(url)
	if not 'Content-Type' in resp.headers or not 'text/plain' in resp.headers['Content-Type']:
		await client.send_message(message.channel, 'Not a plaintext file - cannot read!')
	else:
		markov.buffer_words(username, remove_urls(resp.text))
		markov.add_words(username)
		await client.send_message(message.channel, 'Added to %s with new score: %i' % (username, len(markov.users[username])) )

async def reaction_add(message):
	name = message.content.split(' ')[1]
	url = message.content[len(name) + 1 + 13:]
	if not name in reactions:
		reactions[name] = []

	reactions[name].append(url)

	with open('reactions.json','w') as f:
		json.dump(reactions, f)

	await client.send_message(message.channel, '%s has %i responses.' % (name, len(reactions[name])))

async def reaction_do(message):
	name = message.content[2:]
	if name[0] == ' ':
		name = name[1:]
	if name in reactions and len(reactions[name]) > 0:
		idx = random.choice( range(len(reactions[name])) )
		item = reactions[name][idx]
		await client.send_message(message.channel, '(%i) %s' % (idx,item))

async def reaction_list(message):
	await client.send_message(message.channel, ', '.join( sorted([x for x in list(reactions.keys()) if len(reactions[x]) > 0]) ))

async def reaction_del(message):
	name = message.content.split(' ')[1]
	num = int(message.content.split(' ')[2])
	try:
		marry_poppin = reactions[name].pop(num)

		with open('reactions.json','w') as f:
			json.dump(reactions, f)

		await client.send_message(message.channel, 'Deleted reaction: ```%s```' % marry_poppin)
	except:
		pass

async def do_call_vote(message):
	# spawn a message with the vote, and one upvote and one downvote button
	# wait n seconds
	# delete vote message
	# post new message with vote results
	vote_string = message.content[10:]
	VOTE_LENGTH = 17

	vote = await client.send_message(message.channel, '**Hear, hear! A vote has been called!**\n`%s`' % (vote_string))
	await client.add_reaction(vote, '\U0001F44D')
	await client.add_reaction(vote, '\U0001F44E')

	votes.append({
		'vote_string': vote_string,
		'message': vote,
		'expires': time.time() + VOTE_LENGTH
	})

async def play_5050(message):
	dat = requests.get('https://reddit.com/r/fiftyfifty/.json', headers={'User-Agent':'Discord-Acid-Bot /u/saucecode'}).json()
	urls = [(i['data']['title'], i['data']['url']) for i in dat['data']['children'] if 'imgur.com' in i['data']['url'] or 'i.redd.it' in i['data']['url'] or '5050.degstu' in i['data']['url']]
	titles,url = random.choice(urls)
	await client.send_message(message.channel, '`%s` or...' % titles.split('|')[0].replace('[50/50] ','') )
	await client.send_message(message.channel, '`%s`' % titles.split('|')[1] )
	await asyncio.sleep(5)
	await client.send_message(message.channel, url)

async def do_help(message):
	if not ' ' in message.content:
		await client.send_message(message.channel, HELP_STRINGS['general'])
		return

	page = message.content.split(' ')[1]
	if page in HELP_STRINGS:
		await client.send_message(message.channel, HELP_STRINGS[page])
	else:
		await client.send_message(message.channel, HELP_STRINGS['general'])

async def flip_coin(message):
	await client.send_message(message.channel, 'You rolled ' + random.choice( ['Heads', 'Tails.'] ))

async def voice_request(message):
	# Command behaviour: Join the caller's voice channel if in a voice channel.
	#  Leave the caller's voice channel if already in caller's voice channel.
	#  Move to the caller's voice channel if already in a different voice channel.

	if not voice_wrapper.voice:
		if not message.author.voice.voice_channel:
			await client.send_message(message.channel, 'You must join a voice channel first, %s' % sailor_word())
		else:
			voice_wrapper.voice = await client.join_voice_channel( message.author.voice.voice_channel )
			voice_wrapper.is_ready = True
	else:
		if voice_wrapper.voice.channel == message.author.voice.voice_channel:
			voice_wrapper.streaming_media = False
			await voice_wrapper.voice.disconnect()
			voice_wrapper.voice = None
		else:
			await voice_wrapper.voice.move_to( message.author.voice.voice_channel )

async def voice_say(message):
	if not voice_wrapper.voice:
		await client.send_message(message.channel, 'Run \\voice first, %s' % sailor_word())
		return
	if voice_wrapper.is_ready:
		voice_wrapper.is_ready = False
		tts = gTTS(message.content[5:], lang=voice_wrapper.lang)
		tts.save('voice.wav')
		voice_wrapper.player = voice_wrapper.voice.create_ffmpeg_player('voice.wav', after=voice_wrapper.after)
		voice_wrapper.streaming_media = False
		voice_wrapper.player.start()

async def change_voice_lang(message):
	if not ' ' in message.content:
		await client.send_message(message.channel, 'https://pastebin.com/QxdGXShe')
		return
	lang = message.content.split(' ')[1]
	if lang in gTTS.LANGUAGES:
		voice_wrapper.lang = lang
		await client.send_message(message.channel, 'Selected %s, %s' % (lang, gTTS.LANGUAGES[lang]))
	else:
		await client.send_message(message.channel, 'Not a language, %s' % sailor_word())

async def voice_play_youtube(message):
	if not voice_wrapper.voice:
		await client.send_message(message.channel, 'Run \\voice first, %s' % sailor_word())
		return

	query = message.content[6:]
	if len(query) < 3:
		await client.send_message(message.channel, 'Query is too short.')
		return

	voice_wrapper.queue.append(query)
	messages_to_delete.append({
		'time': time.time() + 3.0,
		'message': await client.send_message(message.channel, 'Added to queue in position %i' % (len(voice_wrapper.queue)-1))
	})

	if voice_wrapper.is_ready:
		voice_wrapper.is_ready = False

		if not voice_wrapper.player or not voice_wrapper.player.is_playing():
			await voice_wrapper.play_next(message.channel)

async def search_songs(message, query):
	files = os.listdir('downloaded/')
	flatten = lambda l: [item for sublist in l for item in sublist]

	if not all([len(x) > 2 for x in query.split(' ')]):
		await client.send_message(message.channel, 'Query must be longer than 2 characters.')
		return

	if '..' in query or '/' in query:
		await client.send_message(message.channel, 'Nice try, Prescott!')
		return []

	# get all files who contain at least one word in the query string
	# example: query = "rick never" will return all files with "rick" and "never" in their names.
	# cases are ignored
	files = list(set(flatten([[x for x in files if q.lower() in x.lower().replace('-','')] for q in query.split(' ')])))

	files_sorted = []
	for f in files:
		count = 0
		for tag in query.split(' '):
			if tag.lower() in f.lower().replace('-',''):
				count += 1
		files_sorted.append( (count, f) )
	files_sorted = [x[1] for x in sorted(files_sorted, reverse=True, key=lambda x:x[0])]
	return files_sorted

async def voice_play_cached(message):
	if not voice_wrapper.voice:
		await client.send_message(message.channel, 'Run \\voice first, %s' % sailor_word())
		return
	files_sorted = await search_songs(message, message.content[6:])

	if len(files_sorted) > 0:
		voice_wrapper.queue.append( (files_sorted[0], 'cache') )
		messages_to_delete.append({
			'time': time.time() + 5.0,
			'message': await client.send_message(message.channel, 'Queueing %s in position %i' % (files_sorted[0], len(voice_wrapper.queue)-1))
		})
	else:
		return

	if voice_wrapper.is_ready:
		voice_wrapper.is_ready = False

		if not voice_wrapper.player or not voice_wrapper.player.is_playing():
			await voice_wrapper.play_next(message.channel)

async def voice_view_queue(message):
	if len(voice_wrapper.queue) == 0:
		await client.send_message(message.channel, 'Nothing in the queue!')
	else:
		lines = []
		for k,item in enumerate(voice_wrapper.queue):
			if type(item) == tuple:
				lines.append('%i. %s' % (k, item[0]))
			else:
				lines.append('%i. (Search) %s' % (k, item))
		await client.send_message(message.channel, 'Current playing queue:\n```%s```' % '\n'.join(lines))

async def voice_pop_queue(message):
	try:
		index = int(message.content.split(' ')[1])
		if index < 1:
			await client.send_message(message.channel, 'Cannot pop from the top of the list %s. Try `\\skip`.' % sailor_word())
			return

		if index >= len(voice_wrapper.queue):
			await client.send_message(message.channel, 'Your number is too big %s.' % sailor_word())
			return

		value = voice_wrapper.queue[index]
		del voice_wrapper.queue[index]

		await client.send_message(message.channel, 'Removed `%s` from the queue.' % (value[0] if type(value) == tuple else value))

	except ValueError:
		await client.send_message(message.channel, 'Needs to be a number, %s. Try `\\queue`.' % sailor_word())

async def voice_stop_youtube(message):
	voice_wrapper.queue.clear()
	voice_wrapper.streaming_media = False
	voice_wrapper.is_ready = True
	if voice_wrapper.player.is_playing():
		voice_wrapper.player.stop()

async def voice_skip_current(message):
	if voice_wrapper.player.is_playing() and voice_wrapper.streaming_media:
		if len(voice_wrapper.queue) == 1:
			await voice_stop_youtube(message)
		else:
			voice_wrapper.player.stop()

async def voice_volume(message):
	value = None
	try:
		value = int(message.content.split(' ')[1])
	except:
		pass

	if not value:
		await client.send_message(message.channel, 'Usage: \\vol [0-100]. Currently set to: %i' % int(100*voice_wrapper.volume) )
	else:
		voice_wrapper.volume = value / 100.0
		if voice_wrapper.player:
			voice_wrapper.player.volume = voice_wrapper.volume

		await client.add_reaction(message, '\U0001F44C')
		# special message for a special guy
		if random.random() > 0.99:
			await client.send_message(message.channel, 'Volume set, daddy.')

async def playlist_add(message):
	playlist_name = message.content.split(' ')[1]
	query = ' '.join(message.content.split(' ')[2:])
	song_list = await search_songs(message, query)

	if len(song_list) == 0:
		return

	song = song_list[0]

	if not playlist_name in playlists:
		playlists[playlist_name] = []

	playlists[playlist_name].append(song)

	save_playlists()

	await client.send_message(message.channel, 'Added `%s` to position %i' % (song, len(playlists[playlist_name])-1))


async def playlist_pop(message):
	playlist_name = message.content.split(' ')[1]

	if not playlist_name in playlists:
		await client.send_message(message.channel, 'Playlist does not exist.')
		return

	position = int(message.content.split(' ')[2])
	if position < len(playlists[playlist_name]) and position >= 0:
		song = playlists[playlist_name].pop(position)
		await client.send_message(message.channel, 'Removed song `%s`' % song)
		if len(playlists[playlist_name]) == 0:
			del playlists[playlist_name]
		save_playlists()
	else:
		await client.send_message(message.channel, 'Nope.jpg')

async def playlist_list(message):
	await client.send_message(message.channel, ', '.join(playlists))

async def playlist_play(message):
	songlist = [(x, 'cache') for x in playlists[message.content.split(' ')[1]]]
	voice_wrapper.queue.extend( random.sample(songlist, k=len(songlist)) ) # random.sample does a shuffle without overwriting the original songlist (immutable random.shuffle)
	if voice_wrapper.is_ready:
		voice_wrapper.is_ready = False

	if not voice_wrapper.player or not voice_wrapper.player.is_playing():
		await voice_wrapper.play_next(message.channel)

async def playlist_list_songs(message):
	playlist_name = message.content.split(' ')[1]

	if not playlist_name in playlists:
		await client.send_message(message.channel, 'Playlist does not exist.')
		return

	if len(playlists[playlist_name]) == 0:
		await client.send_message(message.channel, 'Nothing in the playlist!')
	else:
		lines = []
		for k,item in enumerate(playlists[playlist_name]):
			lines.append('%i. %s' % (k, item))
		await client.send_message(message.channel, 'Playlist contents:\n```%s```' % '\n'.join(lines))

async def do_tell(message):
	target = message.content.split(' ')[1]
	print(target)
	thing_to_tell = message.content[len('\\tell ') + len(target) + 1:]

	mat = re.match('<@.[0-9]+>', target)

	if mat:
		member = discord.utils.get(message.server.members, id=target[2:-1].replace('!',''))
	else:
		member = discord.utils.find(lambda m: target.lower() in m.name.lower() or target.lower() in m.display_name.lower(), message.channel.server.members)

	if not member.id in tells:
		tells[member.id] = []

	tells[member.id].append({'sent_at':time.time(), 'message':thing_to_tell, 'senderid':message.author.id})
	save_tells()

	await client.send_message(message.channel, 'Ok, I\'ll tell %s that next time I see them.' % member.display_name)

async def do_remind(message):
	# \remind [me|@username] [optional: to] [take out the trash] [last:in] [an hour|a minute|a day|a month|n minute/minutes|n second/seconds|n hour/hours]
	subject = message.content.split(' ')[1]

	# determine subject:
	if subject.lower() == 'me':
		subject = message.author
	else:
		mat = re.match('<@.[0-9]+>', subject)

		if mat:
			subject = discord.utils.get(message.server.members, id=subject[2:-1].replace('!',''))
		else:
			subject = discord.utils.find(lambda m: subject.lower() in m.name.lower() or subject.lower() in m.display_name.lower(), message.channel.server.members)

	if type(subject) == str:
		await client.send_message(message.channel, 'I don\'t know who that is...')
		return

	# determine time
	loc = message.content.rfind(' in ')
	time_string = message.content[loc+4:]
	time_seconds = translate_time_string(time_string)

	if time_seconds < 0:
		await client.send_message(message.channel, 'Failed to translate time.')
		return
	#else:
	#	await client.send_message(message.channel, 'Translated time to %.2f seconds / %.2f minutes / %.2f hours / %.2f days' % (time_seconds, time_seconds / 60, time_seconds / 60 / 60, time_seconds / 60 / 60 / 24))

	reminder_content = ' '.join(message.content.split(' ')[2:-3])
	if reminder_content[:3] == 'to ': reminder_content = reminder_content[3:]

	reminder = {'to': subject.id, 'when':time.time() + time_seconds, 'message': reminder_content, 'channel': message.channel.id}
	added = False

	if len(reminders) == 0:
		reminders.append(reminder)
		added = True
	else:
		for key,value in enumerate(reminders):
			if value['when'] >= reminder['when']:
				reminders[key:key] = [reminder]
				added = True
				break

	if not added:
		reminders.append(reminder)
		added = True

	save_reminders()

	await client.send_message( message.channel, 'Ok, I\'ll remind %s in %s' % ('you' if subject == message.author else 'them', humanreadable_time(time_seconds)) )

def humanreadable_time(t):
	out = []
	t = [t]

	def shortcut(o,t,s,i):
		if t[0] / i >= 1:
			o.append('%i %s' % (int(t[0] / i), s))
			while t[0] >= i:
				t[0] -= i

	shortcut(out, t, 'months', 60*60*24*30)
	shortcut(out, t, 'days', 60*60*24)
	shortcut(out, t, 'hours', 60*60)
	shortcut(out, t, 'minutes', 60)
	shortcut(out, t, 'seconds', 1)

	if len(out) == 1:
		return out[0]

	out[-1] = 'and ' + out[-1]

	return ', '.join(out)


def translate_time_string(time_string):
	seconds = -1
	multiplier = 1

	units = {
		'second': 1,
		'minute': 60,
		'hour': 60*60,
		'day': 60*60*24,
		'week': 60*60*24*7,
		'month': 60*60*24*30
	}

	mat = re.match('^an\s|^a\s|[0-9]+\s|[0-9]+\.[0-9]+', time_string)

	if mat:
		try:
			multiplier = float(time_string.split(' ')[0])
		except:
			pass

		word = time_string.split(' ')[1]
		if word in units:
			seconds = units[word]
		elif word[-1] == 's' and word[:-1] in units:
			seconds = units[word[:-1]]

	return seconds * multiplier

async def view_logs(message):
	try:
		token = requests.get(logs_url[1] + '/gentoken?password=%s' % logs_password[0]).text
		await client.send_message(message.channel, 'Logs URL: %s/logs/?t=%s' % (logs_url[0], token))
	except:
		await client.send_message(message.channel, 'Logs server is non-responsive.')

async def make_plop(message):
	img = Image.new('RGB', (256,256), "pink")
	pixels = img.load()

	'''
		function(x,y) {return [min(x+y,255),min(2*x+y,255),min(y*x,255)];}
	'''

	code = message.content[6:]
	with open('tmp_code.js','w') as f:
		f.write(code)

	# get data from javascript:
	# for(a=0; a<20; a++) for(b=0;b<20;b++) console.log(function(x,y){return x+y;}(a,b))
	node_command = """code=(require('fs')).readFileSync('tmp_code.js','utf8');sandbox=(new (require('sandbox')));sandbox.options.timeout=5000;sandbox.run( 'for(a=0; a<256; a++) for(b=0;b<256;b++) console.log((' + code + ')(a,b))', function(o){console.log(JSON.stringify(o));} );"""

	o = subprocess.getoutput('nodejs -e "%s"' % (node_command,))

	if len(o) < 200:
		await client.send_message(message.channel, o)
		return

	pixdata = json.loads(o)

	i = 0
	for y in range(img.size[1]):
		for x in range(img.size[0]):
			i += 1
			if i >= img.size[0] * img.size[1]: break
			pixels[x,y] = tuple( int(a) for a in pixdata['console'][i] )

	img.save('plop.png')
	with open('plop.png','rb') as f:
		await client.send_file(message.channel, f)

markow = {}

async def markowfile(message):
	name = message.content.split(' ')[1]
	for i in name:
		if not i in string.ascii_letters:
			return

	with open('%s.markov.json' % name,'r') as f:
		markow[name] = markovify.Text.from_json(f.read())
		await client.send_message(message.channel, 'Loaded.')

async def imitate_imitate(message):
	name = message.content.split(' ')[1]
	if not name in markow:
		await client.send_message(message.channel, repr(markow))
		return

	await client.send_message(message.channel, markow[name].make_short_sentence(270, tries=10000))

'''
'listadd':       {'run': listadd},
'listpop':       {'run': listpop},
'lists':         {'run': list_lists},
'list':          {'run': view_list}'''

userlists = {}
if not os.path.exists('userlists.json'):
	with open('userlists.json','w') as f:
		json.dump(userlists, f)

with open('userlists.json','r') as f:
	userlists = json.load(f)

async def listadd(message):
	if not message.author.id in userlists:
		userlists[message.author.id] = {}

	listname = message.content.split(' ')[1]
	if not listname in userlists[message.author.id]:
		userlists[message.author.id][listname] = []

	userlists[message.author.id][listname].append( ' '.join(message.content.split(' ')[2:]) )

	with open('userlists.json','w') as f:
		json.dump(userlists, f)

	await client.send_message(message.channel, 'List %s now has %i elements.' % (listname, len(userlists[message.author.id][listname])))

async def listpop(message):
	if not message.author.id in userlists:
		return

	listname = message.content.split(' ')[1]
	if not listname in userlists[message.author.id]:
		await client.send_message(message.channel, 'This list doesn\'t exist, %s' % sailor_word())

	element = int(message.content.split(' ')[2])
	if element >= len(userlists[message.author.id]):
		return

	userlists[message.author.id][listname].pop(element)

	with open('userlists.json','w') as f:
		json.dump(userlists, f)

	await client.send_message(message.channel, 'Popped!')

async def list_lists(message):
	if not message.author.id in userlists:
		return

	await client.send_message(message.channel, '\n'.join( [str(k) + ' ' + v for k,v in enumerate(userlists[message.author.id])] ))

async def view_list(message):
	if not message.author.id in userlists:
		return

	listname = message.content.split(' ')[1]
	if not listname in userlists[message.author.id]:
		await client.send_message(message.channel, 'This list doesn\'t exist, %s' % sailor_word())

	await client.send_message(message.channel, '\n'.join( [str(k) + ' ' + v for k,v in enumerate(userlists[message.author.id][listname])] ))

commander = {
	'help':     {'run': do_help},
	'ping':     {'run': pong},
	'rr':       {'run': get_random_reddit_image},
	'calc':     {'run': do_postfix_calculation},
	'whoami':   {'run': whoami},
	'whois':    {'run': whois},
	'define':   {'run': define_word},
	'ud':       {'run': urban_define_word},
	'rrtop':    {'run': get_random_top_reddit_image},
	#'imitate':  {'run': do_imitate},
	'50/50':    {'run': play_5050},
	'flip':     {'run': flip_coin},
	'tell':     {'run': do_tell},
	'remind':   {'run': do_remind},
	'callvote': {'run': do_call_vote},

	# 'markovsave':    {'run': markov_save},
	# 'markovload':    {'run': markov_load, 'perms':[181227668241383425, 182411730435964928]},
	# 'markovusers':   {'run': markov_users},
	# 'markovclear':   {'run': markov_clear, 'perms':[181227668241383425, 182411730435964928]},
	# 'markovfeed':    {'run': markov_feed, 'perms':[181227668241383425, 304098431973064705, 182411730435964928]},

	'imitate':       {'run': imitate_imitate},
	'markowfile':    {'run': markowfile, 'perms':[181227668241383425, 182411730435964928]},

	'reactionadd':   {'run': reaction_add},
	'reactiondel':   {'run': reaction_del, 'perms':[181227668241383425, 304098431973064705, 182411730435964928]},
	'reactions':     {'run': reaction_list},
	'\\':            {'run': reaction_do},

	'setgame':       {'run': set_game, 'perms':[181227668241383425, 182411730435964928]},
	'rename':        {'run': rename_bot, 'perms':[181227668241383425, 182411730435964928]},

	'voice':         {'run': voice_request},
	'chlang':        {'run': change_voice_lang},
	'tts':           {'run': voice_say},
	'play':          {'run': voice_play_youtube},
	'clay':          {'run': voice_play_cached},

	'queue':         {'run': voice_view_queue},
	'queuepop':      {'run': voice_pop_queue},
	'pladd':         {'run': playlist_add},
	'plpop':         {'run': playlist_pop},
	'pls':           {'run': playlist_list},
	'pl':            {'run': playlist_list_songs},
	'plplay':        {'run': playlist_play},
	'skip':          {'run': voice_skip_current},
	'stop':          {'run': voice_stop_youtube},
	'vol':           {'run': voice_volume},

	'listadd':       {'run': listadd},
	'listpop':       {'run': listpop},
	'lists':         {'run': list_lists},
	'list':          {'run': view_list},

	#'connect4':      {'run': play_connect4},
	#'c4stop':        {'run': stop_connect4},

	'problems':      {'run': mathgame.pose_questionset},
	'ans':           {'run': mathgame.answer_query},
	'scores':        {'run': mathgame.showscores},

	'plop':          {'run': make_plop},

	'logs':          {'run': view_logs}
}

banned_ids = []
banned_counter = [0]
with open('logserver_config.json','r') as f:
	data = json.load(f)
	logs_url = [data['external_server_address'], data['internal_server_address']]
	logs_password = [data['token_generator_password']]

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')

@client.event
async def on_message(message):
	# log all messages
	#>>> CREATE TABLE logs (time real, channel text, id integer, name text, displayname text, messageid integer, deleted integer, edited integer, message text)
	sql_c.execute('INSERT INTO logs VALUES (?,?,?,?,?,?,?,?,?)', (message.timestamp.timestamp(), message.channel.name, int(message.author.id), message.author.name, message.author.display_name, int(message.id), 0, 0, str(message.content)))
	sql.commit()

	if not message.content.startswith('\\') and not message.author.id == client.user.id:
		# buffer words to the users
		'''markov.buffer_words(message.author.name, remove_urls(message.content))
		markov.buffer_words(client.user.name, remove_urls(message.content))

		if message.author.name != markov.last_speaker:
			markov.add_words(markov.last_speaker)
			markov.add_words(client.user.name)

		markov.last_speaker = message.author.name'''
		markov.add_line(message.channel.name, message.author.name, message.content)

	command_was_executed = False

	if message.content.startswith('\\') and len(message.content) > 1 and message.author.id != client.user.id:
		command_candidates = sorted([x.group() for x in [re.match(opt.replace('\\', '\\\\'), message.content[1:]) for opt in list(commander.keys())] if x], key=lambda x:len(x), reverse=True)
		if command_candidates:
			command = commander[command_candidates[0]]
			if not 'perms' in command or int(message.author.id) in command['perms']:
				command_was_executed = True

				if not message.author.id in banned_ids:
					await command['run'](message)

				else:
					banned_counter[0] += 1
					if banned_counter[0] > 10:
						banned_counter[0] = 0
						await client.send_message(message.channel, 'Stop it.')


	# regular message processing

	# check if there is a tell for the sender
	if message.author.id in tells:
		for item in tells[message.author.id]:
			await client.send_message(message.channel, '<@%s> %s (from <@%s>)' % (message.author.id, item['message'], item['senderid']))
		del tells[message.author.id]
		save_tells()

	# complain when someone tries to use \\ but only uses one backslash
	if message.content.startswith('\\'):
		if not command_was_executed and message.content[1:] in [x for x in list(reactions.keys()) if len(reactions[x]) > 0]:
			await client.send_message(message.channel, 'It\'s two backslashes, %s' % sailor_word())

	# complain when someone uses / insteand of \ to call a command
	if message.content.startswith('/'):
		if message.content[1:].split(' ')[0] in commander.keys():
			await client.send_message(message.channel, 'It\'s a backslash, %s' % sailor_word())


@client.event
async def on_message_edit(before, message):
	# log edits
	try:
		sql_c.execute('INSERT INTO logs VALUES (?,?,?,?,?,?,?,?,?)', (message.edited_timestamp.timestamp(), message.channel.name, int(message.author.id), message.author.name, message.author.display_name, int(message.id), 0, 1, str(message.content)))
		sql.commit()
	except AttributeError:
		pass

@client.event
async def on_message_delete(message):
	# log edits
	sql_c.execute('INSERT INTO logs VALUES (?,?,?,?,?,?,?,?,?)', (message.timestamp.timestamp(), message.channel.name, int(message.author.id), message.author.name, message.author.display_name, int(message.id), 1, 0, str(message.content)))
	sql.commit()

async def bot_background_task():
	while not client.is_closed:
		await asyncio.sleep(1)
		if voice_wrapper.player:
			if voice_wrapper.streaming_media and voice_wrapper.player.is_done() and len(voice_wrapper.queue) > 0:
				await voice_wrapper.play_next()

		try:
			if len(reminders) > 0 and reminders[0]['when'] < time.time():
				await client.send_message(discord.utils.get(client.get_all_channels(), id=reminders[0]['channel']), '<@%s> %s' % (reminders[0]['to'], reminders[0]['message']) )
				del reminders[0]
				save_reminders()
		except discord.errors.InvalidArgument:
			pass

		global messages_to_delete
		t = time.time()
		for message in messages_to_delete:
			if message['time'] < t:
				message['deleted'] = 1
				await client.delete_message(message['message'])

		messages_to_delete[:] = [value for value in messages_to_delete if not 'deleted' in value]

		global votes
		t = time.time()
		for v in votes:
			if v['expires'] < t:
				v['message'] = await client.get_message(v['message'].channel, v['message'].id)

				users_voted_for = await client.get_reaction_users([x for x in v['message'].reactions if x.emoji == '\U0001F44D'][0])
				users_voted_against = await client.get_reaction_users([x for x in v['message'].reactions if x.emoji == '\U0001F44E'][0])

				double_voters = len([x for x in users_voted_for if x in users_voted_against]) - 1

				votes_for = [x for x in v['message'].reactions if x.emoji == '\U0001F44D'][0].count - 1 - double_voters
				votes_against = [x for x in v['message'].reactions if x.emoji == '\U0001F44E'][0].count - 1 - double_voters

				await client.delete_message(v['message'])
				if double_voters == 0:
					await client.send_message(v['message'].channel, 'The results are in: `%s`\n**%i for**, **%i against**!' % (v['vote_string'], votes_for, votes_against))
				else:
					await client.send_message(v['message'].channel, 'The results are in: `%s`\n**%i for**, **%i against**! %i %s voted for both, and their votes were not counted.' % (v['vote_string'], votes_for, votes_against, double_voters, 'person' if double_voters == 1 else 'people'))

		votes[:] = [v for v in votes if v['expires'] > t]

with open('secrettoken', 'r') as f:
	client.loop.create_task(bot_background_task())
	client.run(f.read())
