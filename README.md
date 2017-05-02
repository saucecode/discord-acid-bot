# Acid-Bot
My personal Discord chat bot, written in Python 3

`acid-bot` runs on **Python 3.4+** (tested only on 3.5) and requires [gTTS](https://github.com/pndurette/gTTS) (Python TTS library), [discord.py](https://github.com/Rapptz/discord.py/) (Discord Bot API wrapper for Python) and `requests`. It also requires my postfix calculator implementation, but this is included (`postfix.py`).

On start-up, the Discord API token must be read from file `secrettoken` in the same directory.

## Currently implemented commands

	\help                This helpful message.
	\rr [subreddit]      Get a random image from [subreddit]
	\rrtop [subreddit]   Get a random image from the all time top posts of [subreddit]
	\calc [query]        Postfix calculator
	\whoami              User stats
	\whois [username]    ^ Ditto
	\ping                Pong.
	\define [word]       Lookup the definition of [word]
	\ud [word]           Lookup the urban definition of [word]
	\50/50               You feeling lucky?
	\flip                Flip a coin
	\tell [name] [msg]   Send [msg] to [name] next time the bot sees them. [name] can be a @mention or a username.

	\imitate [username] (length) (tts)  Imitate [username] (Markov Chains!).
	\markovusers         List users' markov ratings (higher number means better \imitate)
	\markovsave          Save markov data to disk

	\reactionadd [name] [url]  Add a new link to the [name] collection
	\reactions                 Lists all the reaction collections
	\\[name]                   Random link from [name] collection (TWO backslashes)

	\voice               Connect/disconnect from voice channel
	\tts                 Say something with the tts
	\chlang              Changes the tts language (from https://pastebin.com/QxdGXShe)

	\scores                List math scores
	\problems              Start a short 10 question basic facts test
	\ans [ans1] [ans2] ... Answer the basic facts test

	Debug (Admin) Commands:
	\markovload \markovclear [username] \markovfeed [username] [url]
	\rename [newname] \setgame [playing] \reactiondel [name] [num]

Everything is functional. Improvements are needed on the math-quiz commands and the markov bot imitation fails to produce interesting output.

TTS feature is supplied using Google Translate's TTS API (Note: Official Discord Bot API does not let bots listen to the chat).

`\tell` will keep a message for a person, and send it next time that person sends a message on a channel. The messages are stored in `tells.json`.

### Additional features/notes

 - The bot logs all messages, edits, and deletions into an sqlite3 database `logs.db`. This is to counter censorship.
 - The bot saves all reactions to a `reactions.json`. This file can be edited directly, but the bot must be restarted to take the changes.
 - Word-pair data for the markov bot is stored in `markov.pickle`. This data is **not** saved unless the `\markovsave` command is run.
 - Math-quiz score data is storred in `mathscores.json`.
 - The `[url]` supplied to `\markovfeed` must point to a resource with `Content-Type: text/plain`.
 - Permissions are defined per-command hardcoded into the bot. Change them to your liking. Use IDs given by `\whoami` and `\whois` commands.
 - You do not need to type the whole username for `\whois` to work. The first few letters will be sufficient.
