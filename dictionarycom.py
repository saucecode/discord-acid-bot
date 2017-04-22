#dictionarycom

import requests, re, urllib

def get_definitions(word):
	html = requests.get('http://www.dictionary.com/browse/%s' % word).text
	if 'There are no results for: ' in html: return []
	definition_block = html.split('<div class="def-list">')[1].split('</section>')[0]
	definitions = definition_block.split('<div class="def-set">')[1:]
	strings = [ re.sub(' +',' ', re.sub('<[^<]+?>', '', i.split('<div class="def-content">')[1].split('</div>')[0].strip()).strip()) for i in definitions ]
	return strings

def get_urban_definitions(word):
	url = 'http://api.urbandictionary.com/v0/define?term=%s' % urllib.parse.quote(word)
	dat = requests.get(url).json()
	return dat['list']