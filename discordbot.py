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
from PIL import Image

from functools import reduce

discord.opus.load_opus('libopus.so.0')

from gtts import gTTS
from youtube_dl import YoutubeDL

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
		ydl = YoutubeDL( {'outtmpl': 'downloaded/%(title)s-%(id)s.%(ext)s', 'format': 'bestaudio/best', 'default_search': 'ytsearch', 'cachedir':'downloaded', 'nopart':'true'} )
		entries = ydl.extract_info(query, download=False)
		if 'entries' in entries:
			entries = entries['entries']

		if len(entries) == 0:
			await client.send_message(channel, 'Can\'t find anything :L')

		else:
			entry = entries[0] if type(entries) == list else entries
			await client.send_message(channel, 'Getting audio for: **%s** ' % (entry['title']))

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

reactions = {}
if os.path.exists('reactions.json'):
	with open('reactions.json','r') as f:
		reactions = json.load(f)

tells = {}
if os.path.exists('tells.json'):
	with open('tells.json','r') as f:
		tells = json.load(f)

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

remove_urls = lambda x:re.sub(r'^https?:\/\/.*[\r\n]*', '', x, flags=re.MULTILINE)

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
\tell @[name] [msg]   Send [msg] to @[name] next time the bot sees them.

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
\skip                Skip current song
\stop                Stop playback. Discards queue.

\tts                 Say something with the tts
\chlang              Changes the tts language (from https://pastebin.com/QxdGXShe)

\scores                List math scores
\problems              Start a short 10 question basic facts test
\ans [ans1] [ans2] ... Answer the basic facts test

\logs               Generates a link to the logs.

Debug (Admin) Commands:
\markovload \markovclear [username] \markovfeed [username] [url]
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

async def play_5050(message):
	dat = requests.get('https://reddit.com/r/fiftyfifty/.json', headers={'User-Agent':'Discord-Acid-Bot /u/saucecode'}).json()
	urls = [(i['data']['title'], i['data']['url']) for i in dat['data']['children'] if 'imgur.com' in i['data']['url'] or 'i.redd.it' in i['data']['url'] or '5050.degstu' in i['data']['url']]
	titles,url = random.choice(urls)
	await client.send_message(message.channel, '`%s` or...' % titles.split('|')[0].replace('[50/50] ','') )
	await client.send_message(message.channel, '`%s`' % titles.split('|')[1] )
	await asyncio.sleep(5)
	await client.send_message(message.channel, url)

async def do_help(message):
	await client.send_message(message.channel, HELP_STRING)

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
	await client.send_message(message.channel, 'Added to queue.')

	if voice_wrapper.is_ready:
		voice_wrapper.is_ready = False

		if not voice_wrapper.player or not voice_wrapper.player.is_playing():
			await voice_wrapper.play_next(message.channel)

async def voice_stop_youtube(message):
	if voice_wrapper.player.is_playing():
		voice_wrapper.queue.clear()
		voice_wrapper.streaming_media = False
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
	'imitate':  {'run': do_imitate},
	'50/50':    {'run': play_5050},
	'flip':     {'run': flip_coin},
	'tell':     {'run': do_tell},
	'remind':   {'run': do_remind},

	'markovsave':    {'run': markov_save},
	'markovload':    {'run': markov_load, 'perms':[181227668241383425]},
	'markovusers':   {'run': markov_users},
	'markovclear':   {'run': markov_clear, 'perms':[181227668241383425]},
	'markovfeed':    {'run': markov_feed, 'perms':[181227668241383425, 304098431973064705]},

	'reactionadd':   {'run': reaction_add},
	'reactiondel':   {'run': reaction_del, 'perms':[181227668241383425, 304098431973064705, 182411730435964928]},
	'reactions':     {'run': reaction_list},
	'\\':            {'run': reaction_do},

	'setgame':       {'run': set_game, 'perms':[181227668241383425]},
	'rename':        {'run': rename_bot, 'perms':[181227668241383425]},

	'voice':         {'run': voice_request},
	'chlang':        {'run': change_voice_lang},
	'tts':           {'run': voice_say},
	'play':          {'run': voice_play_youtube},
	'skip':          {'run': voice_skip_current},
	'stop':          {'run': voice_stop_youtube},
	'vol':           {'run': voice_volume},

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

		await asyncio.sleep(1)

with open('secrettoken', 'r') as f:
	client.loop.create_task(bot_background_task())
	client.run(f.read())
