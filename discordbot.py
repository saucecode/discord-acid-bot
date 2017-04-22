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
		if os.path.exists('markov.pickle'):
			self.load()
	
	def add_words(self, userid, words):
		if '. ' in words:
			for sentence in words.split('. '):
				self.add_words(userid, sentence)
			return
		
		sterile = re.sub(' +',' ',re.sub(r'[^a-zA-Z0-9\ ]', '', words.replace('\r','').replace('\n',' ').replace('\t', ' ')).strip().lower())
		
		if not userid in self.users:
			self.users[userid] = {}
		
		if not userid in self.users_incomplete:
			self.users_incomplete[userid] = []
			
		if len(sterile.split(' ')) < 3:
			self.users_incomplete[userid].extend(sterile.split(' '))

		else:
			sterile = ' '.join(self.remove_duplicates(self.users_incomplete[userid])) + ' ' + sterile
			self.users_incomplete[userid].clear()
			
			for triple in self.get_triples(sterile):
				if not triple[:2] in self.users[userid]:
					self.users[userid][triple[:2]] = []
			
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

\imitate [username] (length) (tts)  Imitate [username] (Markov Chains!).
\markovusers         List users' markov ratings (higher number means better \imitate)
\markovsave          Save markov data to disk

Debug (Admin) Commands:
\markovload \markovclear [username] \markovfeed [username] [url]
\rename [newname] \setgame [playing]```'''


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
		markov.add_words(message.author.name, remove_urls(message.content))
		markov.add_words(client.user.name, remove_urls(message.content))
	
	if message.content.startswith('\\rr'):
		subreddit = message.content.split(' ')[1]
		dat = requests.get('https://reddit.com/r/' + subreddit + '/.json', headers={'User-Agent':'Discord-Acid-Bot /u/saucecode'}).json()
		urls = [i['data']['url'] for i in dat['data']['children']]
		imgurs = [i for i in urls if 'imgur.com' in i or 'i.redd.it' in i]
		await client.send_message(message.channel, random.choice(imgurs))
	
	elif message.content.startswith('/r'):
		await client.send_message(message.channel, 'It\'s a backslash, %s.' % sailor_word())
	
	elif message.content.startswith('\\calc'):
		await client.send_message(message.channel, postfix.outputResult( postfix.doPostfix(message.content[6:]) ))

	elif message.content.startswith('\\whoami'):
		#await client.edit_profile(username=message.content.split(' ')[1])
		await client.send_message(message.channel, 'Name: %s; Display Name: %s; Discriminator: %s; ID: %s' % (message.author.name, message.author.display_name, message.author.discriminator, message.author.id))
	
	elif message.content.startswith('\\whois'):
		target = message.content[7:]
		member = discord.utils.find(lambda m: target.lower() in m.name.lower() or target.lower() in m.display_name.lower(), message.channel.server.members)
		if member:
			await client.send_message(message.channel, 'Name: %s; Display Name: %s; Discriminator: %s; ID: %s' % (member.name, member.display_name, member.discriminator, member.id))
		else:
			await client.send_message(message.channel, 'I can\'t find a %s' % (target,))

	elif message.content.startswith('\\rename') and int(message.author.id) == 181227668241383425:
		await client.edit_profile(username=message.content.split(' ')[1])
		await client.send_message(message.channel, 'Acknowledged.')
	
	elif message.content.startswith('\\setgame') and int(message.author.id) == 181227668241383425:
		await client.change_presence(game=discord.Game(name=message.content[9:]))
	
	elif message.content.startswith('\\ping'):
		await client.send_message(message.channel, '%s pong.' % (message.author.mention))
	
	elif message.content.startswith('\\define'):
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
	
	elif message.content.startswith('\\ud'):
		word = message.content[4:]
		definition = dictionary.get_urban_definitions(word)[0]
		for i in range(len(definition['definition'])//2000 + 1):
			await client.send_message(message.channel, '```%s```' % definition['definition'][i*2000:i*2000+2000])
		await client.send_message(message.channel, '```examples: %s```' % definition['example'])
	
	elif message.content.startswith('\\imitate'):
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
	
	elif message.content.startswith('\\markovsave'):
		markov.save()
		await client.send_message(message.channel, 'Saved markov.json')
	
	elif message.content.startswith('\\markovload') and int(message.author.id) == 181227668241383425:
		markov.load()
		await client.send_message(message.channel, 'Loaded markov.json')
	
	elif message.content.startswith('\\markovusers'):
		await client.send_message(message.channel,
			', '.join( ['%s (%i)' % (key, len(markov.users[key])) for key in list(markov.users.keys())] )
		)
	
	elif message.content.startswith('\\markovclear') and int(message.author.id) == 181227668241383425:
		target = message.content[13:]
		if target in markov.users:
			del markov.users[target]
			await client.send_message(message.channel, 'Cleared markov data for %s' % (target,))
		else:
			await client.send_message(message.channel, 'Could not find %s in markov.users' % (target,))
	
	elif message.content.startswith('\\markovfeed') and int(message.author.id) in [181227668241383425, 304098431973064705]:
		username = message.content.split(' ')[1]
		url = message.content.split(' ')[2]
		resp = requests.get(url)
		if not 'Content-Type' in resp.headers or not 'text/plain' in resp.headers['Content-Type']:
			await client.send_message(message.channel, 'Not a plaintext file - cannot read!')
		else:
			markov.add_words(username, remove_urls(resp.text))
			await client.send_message(message.channel, 'Added to %s with new score: %i' % (username, len(markov.users[username])) )
	
	elif message.content.startswith('\\50/50'):
		dat = requests.get('https://reddit.com/r/fiftyfifty/.json', headers={'User-Agent':'Discord-Acid-Bot /u/saucecode'}).json()
		urls = [(i['data']['title'], i['data']['url']) for i in dat['data']['children'] if 'imgur.com' in i['data']['url'] or 'i.redd.it' in i['data']['url'] or '5050.degstu' in i['data']['url']]
		titles,url = random.choice(urls)
		await client.send_message(message.channel, '`%s` or...' % titles.split('|')[0].replace('[50/50] ','') )
		await client.send_message(message.channel, '`%s`' % titles.split('|')[1] )
		await asyncio.sleep(7)
		await client.send_message(message.channel, url)
	
	elif message.content.startswith('\\help'):
		await client.send_message(message.channel, HELP_STRING)

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
