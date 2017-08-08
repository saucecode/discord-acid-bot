import random

__firsts =  'shit fuck muffin dumb piss muppet mother goat whore ass pussy cock fugly swamp cake tart old tasteless'.split(' ')
__seconds = 'cunt bitch tard face fuck stain stick muppet fucker ass face bandit eater fart lard'.split(' ')
__singles = [
	'cuck', 'muppet', 'sex offender', 'cumslut', 'reasonable human being', 'buffoon', 'ignoramus', 'dense mother fucker',
	'FOOL!', 'mouth breather', 'imbecile', 'waste of space', 'withered old hag', 'statistician'
]

def sailor_word():
	if random.random() > len(__singles) / ( (len(__firsts) + len(__seconds)) ):
		f = random.choice(__firsts)
		s = random.choice([x for x in __seconds if not x == f])
		return '%s%s' % (f, s)
	else:
		return 'you %s' % random.choice(__singles)
