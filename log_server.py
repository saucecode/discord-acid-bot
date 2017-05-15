from flask import *
import random, sqlite3, time, html, string, json

app = Flask(__name__)

active_tokens = {}
appinfo = {'password':'password', 'token_lifetime': 60*60}

with open('logserver_config.json', 'r') as f:
	data = json.load(f)
	appinfo['password'] = data['token_generator_password']
	appinfo['token_lifetime'] = data['token_lifetime']
	appinfo['server_port'] = data['logserver_port']

random_string = lambda x:''.join([random.choice(string.hexdigits) for i in range(x)])

@app.route('/gentoken')
def generate_access_token():
	if not request.args.get('password') == appinfo['password']:
		return abort(403)

	token = random_string(12)
	birthday = time.time()
	expiry = birthday + appinfo['token_lifetime']
	active_tokens[token] = {'created':birthday, 'expires':expiry}

	return Response(token, mimetype='text/plain')

@app.route('/logs/')
def logs_home():
	if request.args.get('t'):
		r = make_response(redirect('/logs/'))
		r.set_cookie('token',request.args.get('t'))
		return r

	if not request.cookies.get('token') in active_tokens:
		return abort(403)

	if active_tokens[request.cookies.get('token')]['expires'] < time.time():
		del active_tokens[request.cookies.get('token')]
		return 'Your token has expired. Get a new one.'

	return '<a href="/logs/textcat/everything/">#textcat</a><br/><a href="/logs/bots/everything/">#bots</a><br/>#kewlkids : Not in channel<br/>'


@app.route('/logs/<channelname>/everything/')
def view_channel_logs(channelname=None):
	if not request.cookies.get('token') in active_tokens:
		return abort(403)

	if active_tokens[request.cookies.get('token')]['expires'] < time.time():
		del active_tokens[request.cookies.get('token')]
		return 'Your token has expired. Get a new one.'

	conn = sqlite3.connect('logs.db')
	c = conn.cursor()

	after = float(request.args.get('after') or 0) # unix epoch date in seconds
	query = "SELECT * from logs WHERE channel=? AND time>?"
	c.execute(query, [(channelname), after])

	results = c.fetchmany(500) # fetch 500 messages, deletions and edits

	conn.close()

	# format each message into a HTML line
	formatted_results = []
	for result in results:
		formatted_results.append('{} {} {}: {} {} {}'.format(
			result[5],
			time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(result[0])),
			html.escape(result[1]),
			html.escape('(' + result[3] + ')'),
			html.escape('<' + result[4] + '>'),
			('<strong>EDITED</strong> ' if result[7] == 1 else '')
			+ ('<strong>DELETED</strong> ' if result[6] == 1 else '') + html.escape(result[-1])
		))

	body = '<br/>\n'.join(formatted_results)

	# generate log history navigation links
	nextpage = 'There are no more pages.'
	if len(results) == 500:
		nextpage = '<a href="/logs/%s/everything/?after=%s">next page</a>' % (channelname,results[-1][0])

	pastday = '<a href="/logs/%s/everything/?after=%s">Latest (24 hours ago)</a>' % (channelname, time.time()-24*60*60)
	goback = '<a href="/logs/%s/everything/?after=%s">Go back 24 hours</a>' % (channelname, after-24*60*60)
	firstpage = '<a href="/logs/%s/everything/?after=0">Oldest</a>' % channelname

	resp = Response('''<!DOCTYPE html>
<html>
	<head>
		<title>logs</title>
		<style>
			body {
				font-family: monospace;
			}
		</style>
	</head>
	<body>
		%s | %s | %s | %s
		<hr/>
		%s
		<hr/>
		%s | %s
	</body>
</html>
''' % (firstpage, nextpage,goback,pastday,body,nextpage,goback), mimetype='text/html')
	return resp

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=appinfo['server_port'], debug=False, threaded=True)
