import random

__firsts =  'shit fuck muffin dumb piss muppet mother goat whore ass pussy cock'.split(' ')
__seconds = 'cunt bitch tard face fuck stain stick muppet fucker ass face bandit'.split(' ')

def sailor_word():
	f = random.choice(__firsts)
	s = random.choice([x for x in __seconds if not x == f])
	return '%s%s' % (f, s)