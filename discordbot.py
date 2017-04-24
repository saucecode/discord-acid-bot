import discord
import asyncio
import requests
import random
import sqlite3
import re
import json
import pickle
import os

import postfix
import dictionarycom as dictionary
from sailortalk import sailor_word

client = discord.Client()
sql = sqlite3.connect('logs.db')
sql_c = sql.cursor()

class Markov():
	def __init__(self):
		self.users = {}
		self.users_incomplete = {}
		self.last_speaker = ''
		if os.path.exists('markov.pickle'):
			self.load()

	def buffer_words(self, userid, words):
		if not userid in self.users:
			self.users[userid] = {}

		if not userid in self.users_incomplete:
			self.users_incomplete[userid] = []

		sterile = re.sub(r'[^a-zA-Z0-9\ ]', '', words.replace('\r','').replace('\n',' ').replace('\t', ' ')).strip().lower()
		sterile = sterile.split(' ')

		sterile = re.sub(' +',' ', ' '.join( [x for x in sterile if not re.findall('[0-9]{14}.$', x)] )) # remove mentions and emotes

		self.users_incomplete[userid].extend(sterile.split(' '))

	def add_words(self, userid):
		if not userid in self.users:
			self.users[userid] = {}

		if not userid in self.users_incomplete:
			self.users_incomplete[userid] = []


		words = ' '.join(self.users_incomplete[userid])

		if '. ' in words:
			for sentence in words.split('. '):
				self.add_words(userid, sentence)
			return

		sterile = re.sub(' +',' ',re.sub(r'[^a-zA-Z0-9\ ]', '', words.replace('\r','').replace('\n',' ').replace('\t', ' ')).strip().lower())

		if len(sterile.split(' ')) < 3:
			self.users_incomplete[userid].extend(sterile.split(' '))

		else:
			sterile = ' '.join(self.remove_duplicates(self.users_incomplete[userid])) + ' ' + sterile
			self.users_incomplete[userid].clear()

			for triple in self.get_triples(sterile):
				if not triple[:2] in self.users[userid]:
					self.users[userid][triple[:2]] = []

				if not triple[2] in self.users[userid][triple[:2]]:
					self.users[userid][triple[:2]].append(triple[2])

	def get_triples(self, words):
		words_split = words.split(' ')
		triples = []
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


markov = Markov()

reactions = {}
if os.path.exists('reactions.json'):
	with open('reactions.json','r') as f:
		reactions = json.load(f)

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

\imitate [username] (length) (tts)  Imitate [username] (Markov Chains!).
\markovusers         List users' markov ratings (higher number means better \imitate)
\markovsave          Save markov data to disk

\reactionadd [name] [url]  Add a new link to the [name] collection
\reactions                 Lists all the reaction collections
\\[name]                   Random link from [name] collection (TWO backslashes)

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

	await client.send_message(message.channel, random.choice(imgurs) + ' TOP!')

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
	await whois_user(message.channel, message.author)

async def whois(message):
	target = message.content[7:]
	member = discord.utils.find(lambda m: target.lower() in m.name.lower() or target.lower() in m.display_name.lower(), message.channel.server.members)
	if member:
		await whois_user(message.channel, member)
	else:
		await client.send_message(message.channel, 'I can\'t find a %s' % (target,))

async def whois_user(chan, user):
	await client.send_message(chan, 'Name: %s; Display Name: %s; Discriminator: %s; ID: %s' % (user.name, user.display_name, user.discriminator, user.id))

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
		await client.send_message(message.channel, '`%s`' % (markov.imitate(name, max_length=max_length),), tts='tts' in opts)

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
	await client.send_message(message.channel, ', '.join( [x for x in list(reactions.keys()) if len(reactions[x]) > 0] ))

async def reaction_del(message):
	name = message.content.split(' ')[1]
	num = int(message.content.split(' ')[2])
	try:
		reactions[name].pop(num)

		with open('reactions.json','w') as f:
			json.dump(reactions, f)
	except:
		pass

async def play_5050(message):
	dat = requests.get('https://reddit.com/r/fiftyfifty/.json', headers={'User-Agent':'Discord-Acid-Bot /u/saucecode'}).json()
	urls = [(i['data']['title'], i['data']['url']) for i in dat['data']['children'] if 'imgur.com' in i['data']['url'] or 'i.redd.it' in i['data']['url'] or '5050.degstu' in i['data']['url']]
	titles,url = random.choice(urls)
	await client.send_message(message.channel, '`%s` or...' % titles.split('|')[0].replace('[50/50] ','') )
	await client.send_message(message.channel, '`%s`' % titles.split('|')[1] )
	await asyncio.sleep(7)
	await client.send_message(message.channel, url)

async def do_help(message):
	await client.send_message(message.channel, HELP_STRING)

async def flip_coin(message):
	await client.send_message(message.channel, 'You rolled ' + random.choice( ['Heads', 'Tails.'] ))

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

	'markovsave':    {'run': markov_save},
	'markovload':    {'run': markov_load, 'perms':[181227668241383425]},
	'markovusers':   {'run': markov_users},
	'markovclear':   {'run': markov_clear, 'perms':[181227668241383425]},
	'markovfeed':    {'run': markov_feed, 'perms':[181227668241383425, 304098431973064705]},

	'reactionadd':   {'run': reaction_add},
	'reactiondel':   {'run': reaction_del, 'perms':[181227668241383425, 304098431973064705]},
	'reactions':     {'run': reaction_list},
	'\\':            {'run': reaction_do},

	'setgame':       {'run': set_game, 'perms':[181227668241383425]},
	'rename':        {'run': rename_bot, 'perms':[181227668241383425]}
}


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
		markov.buffer_words(message.author.name, remove_urls(message.content))
		markov.buffer_words(client.user.name, remove_urls(message.content))

		if message.author.name != markov.last_speaker:
			markov.add_words(markov.last_speaker)
			markov.add_words(client.user.name)

		markov.last_speaker = message.author.name


	if message.content.startswith('\\') and len(message.content) > 1:
		command_candidates = sorted([x.group() for x in [re.match(opt.replace('\\', '\\\\'), message.content[1:]) for opt in list(commander.keys())] if x], key=lambda x:len(x), reverse=True)
		if command_candidates:
			command = commander[command_candidates[0]]
			if not 'perms' in command or int(message.author.id) in command['perms']:
				await command['run'](message)


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

with open('secrettoken', 'r') as f:
	client.run(f.read())
