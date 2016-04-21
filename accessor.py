from flask import Flask, request , make_response , render_template
from spacy.en import English
import socket
import subprocess

import argparse , sys
import json
import time
import datetime

################
# DEFAULT VALUES
################
STANFORD_MODEL = 'models/wsj-0-18-left3words-nodistsim.tagger'
STANFORD_SEPARATOR = '_'
STANFORD_HOST = 'localhost'
STANFORD_PORT = 2020
STANFORD_TIMEOUT = 5 # in seconds

ERROR_FILE = 'error.log'

TEST_SENTENCE = """Much I marveled this ungainly fowl to hear discourse so plainly; though its answer little meaning - little relevancy bore."""
NO_TEXT_ERROR = """No 'text' to process supplied. Use spacy_rest?text=This+is+an+example."""
NO_TEXT_ERROR_D = """No 'text' to process supplied. Use the following: curl -d text="This is an example"""

# Needs to be launched here, so Flask can deal
# With the decorators
app = Flask(__name__)

##################
# HELPER FUNCTIONS
##################
def verbose(*args):
	try:
		if arguments.verbose:
			for arg in args:
				print(arg)
	except NameError:
		# arguments.verbose is not defined
		pass

# https://www.andreas-jung.com/contents/a-python-decorator-for-measuring-the-execution-time-of-methods
def timeit(f):
	def timed(*args, **kw):

		ts = time.time()
		result = f(*args, **kw)
		te = time.time()

		verbose("'{}()' executed in {:2.3f} seconds.".format(f.__name__,(te-ts)))
		return result

	return timed

def error_html(error,dump=False,input_text=False):
	if not input_text:
		input_text = TEST_SENTENCE
	return(render_template('index.html',error=error,input_text=input_text,dump=dump))

def error_log(error,error_file=ERROR_FILE):
	verbose(error)
	with open(error_file,'a') as f:
		f.write(str(datetime.datetime.utcnow()) + "\n")
		try:
			f.write(str(error))
		except Exception:
			f.write("Error could not be written.")
		
		f.write("\n\n")

@app.errorhandler(404)
def not_found(error):
	return(render_template('index.html',error="Page not found",page_not_found="true"),404)

###################
# GENERAL STRUCTURE
###################
# 1: use Flask to give text to parse
# 2.1: use Stanford to tag
# 2.2: use spaCy to parse
# 3: return PubAnnotate JSON (which can be visualized in TextAE)

##############
# FLASK THINGS
##############
@app.route('/spacy_rest', methods = ['GET', 'POST'])
def rest():
	"""Used to make requests such as:
	   curl 127.0.0.1:5000/spacy_rest?text=This+is+a+test
	   and to serve the HTML"""
	
	# Request made via cURL, so we serve JSON
	verbose("Received {} request at /spacy_rest (no trailing slash).".format(request.method))
	if request.method == 'POST' or 'curl' in request.headers['User-Agent'].lower():
		
		# 'text' can hide either in request.args or request.form
		if 'text' in request.args and request.args['text'] is not '':
			try:
				json_ = text_to_json(request.args['text'])
				return(json_to_response(json_))
			except Exception as e:
				error_log(e)
				return("Error while processing request for '{}'. Check {} for more information.\n".format(request.args['text'],ERROR_FILE),500)
			
		if 'text' in request.form and request.form['text'] is not '':
			try:
				json_ = text_to_json(request.form['text'])
				return(json_to_response(json_))
			except Exception as e:
				error_log(e)
				return("Error while processing request for '{}'. Check {} for more information.\n".format(request.form['text'],ERROR_FILE),500)
				
		return(NO_TEXT_ERROR,400)
	
	# serve HTML
	if request.method == 'GET':
		if 'text' in request.args:
			
			if request.args['text'] is '':
				return(error_html(NO_TEXT_ERROR),400)
			
			try:
				json_ = text_to_json(request.args['text'])
				pretty_json = json.dumps(str(json.loads(json_)),sort_keys=True,indent=4)
				return(render_template('index.html',json=json_,pretty_json=pretty_json,input_text=request.args['text']),200)
			
			except Exception as e:
				error_log(e)
				return(error_html("Error processing GET request for '{}'".format(request.args['text']),
								  dump=e,
								  input_text=request.args['text']),500)
				
		
		# some other fantasy argument supplied
		if len(request.args) > 0:
			return(error_html(NO_TEXT_ERROR),400)
	
	return(render_template('index.html',input_text=TEST_SENTENCE),300)

@app.route('/spacy_rest/' , methods = ['GET','POST'])
def rest_d():
	"""Make requests using curl -d, handing a 'text' to the request."""

	if request.headers['Content-Type'] == 'application/json':
		if 'text' in request.get_json():
			try:
				json_ = text_to_json(request.get_json()['text'])
				return(json_to_response(json_))
			except Exception as e:
				error_log(e)
				return("Error while processing request for '{}'. Check {} for more information.\n".format(request.get_json()['text'],ERROR_FILE),500)
		return(NO_TEXT_ERROR_D,400)
	
	if request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
		if 'text' in request.form:
			try:
				json_ = text_to_json(request.form['text'])
				return(json_to_response(json_))
			except Exception as e:
				error_log(e)
				return("Error while processing request for '{}'. Check {} for more information.\n".format(request.form['text'],ERROR_FILE),500)
		return(NO_TEXT_ERROR_D,400)
		
	return("Unsupported media type.",415)
		
def json_to_response(json_):
	response = make_response(json_)
	
	# This is necessary to allow the REST be accessed from other domains
	response.headers['Access-Control-Allow-Origin'] = '*'

	response.headers['Content-Type'] = 'application/json'
	response.headers['Content-Length'] = len(json_)
	response.headers['X-Content-Type-Options'] = 'nosniff'
	response.headers['charset'] = 'utf-8'
	return(response)
	
#################
# ACTUAL PIPELINE
#################

@timeit
def text_to_json(text):
	"""Coordinates the entire pipeline"""

	verbose("Starting pipeline on the following text: {}".format(text))

	# Stanford Tagger does not like \n
	text_delined = text.replace('\n',' ')

	try:
		verbose("Asking Stanford...")
		tokens = ask_stanford(text_delined)
		verbose("Tokenized as follows:\n{}\n".format(tokens))

		verbose("Transforming lists...")
		tokens, tags = stanford_to_lists(tokens)
		verbose("Split lists as follows:\n{0} tokens: {1}\n{2} tags: {3}".format(len(tokens),tokens,len(tags),tags))

		verbose("Parsing with spaCy...")
		doc = lists_to_spacy(tokens,tags,SPACY)
		verbose("Loaded lists into spaCy\n")

		verbose("Convert spaCy to JSON...")
		json_ = spacy_to_json(doc,text)
		verbose("Producing JSON:\n{}\n".format(json_))

		return(json_)
	except Exception as e:
		raise(e)

@timeit
def stanford_socket(host=STANFORD_HOST,port=STANFORD_PORT):
	"""Creates a socket to Stanford server"""
	s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	s.connect((host,port))
	return(s)

@timeit
def ask_stanford(text,expected=1024,timeout=STANFORD_TIMEOUT):
	"""Sends message to socket where Stanford server is listening and reads reply"""
	
	s = stanford_socket()
	
	# Send question (needs to be in bytes)
	if not isinstance(text, bytes):
		try:
			verbose("Text needs to be converted to bytes.")
			text = text.encode()
		except Exception as e:
			raise(e)
			s.close()
			return
	
	verbose("Sending question to Stanford...")		
	s.sendall(text)
	s.shutdown(socket.SHUT_WR)
	
	# Read reply
	reply = ""
	now = time.time()
	while True:
		data = s.recv(expected)
		if data == b'':
			break
		reply += data.decode()
		
		if ( time.time() - now ) > timeout:
			s.close()
			raise(Exception.TimeoutError("Stanford failed to reply within {} seconds.".format(timeout)))
			break
	
	s.close()
	verbose(reply)
	return(split_stanford(reply))

@timeit	
def split_stanford(text,separator=STANFORD_SEPARATOR):
	"""Splits Stanford output while allowing for tokens to contain spaces"""

	tokens = list()
	previous_element = ''
	for element in text.strip().split():
		if separator in element:
			if len(previous_element) > 0:
				element = previous_element + element
			tokens.append(element)
			previous_element = ''

		else:
			previous_element = (previous_element + " " + element).strip()
			
	return(tokens)

@timeit
def stanford_to_lists(tokens,separator=STANFORD_SEPARATOR):
	"""Extracts tags and tokens from Stanfords representation. Different models use different separators, usually '/' or '_'"""
	token_list = list()
	tag_list = list()

	for element in tokens:

		# Stanford changes some tokes, we need to revert this
		
		# -LBR- and -RRB-
		token = separator.join(element.split(separator)[:-1])
		tag = element.split(separator)[-1]

		if token == '-LRB-':
			token_list.append("(")

		elif token == '-RRB-':
			token_list.append(")")
			
		# as well as -LSB- and -RSB-
		elif token == '-LSB-':
			token_list.append("[")
		
		elif token == '-RSB-':
			token_list.append("]")
			
		# Stanfords `` and '' (opening + closing quotes)
		elif token == '``':
			token_list.append("\"")
			
		elif token == '`':
			token_list.append("\'")
			
		elif token == '\'\'':
			token_list.append("\"")

		else:
			token_list.append(token)
		
		tag_list.append(tag)
		
	if not len(token_list) == len(tag_list):
		raise(Exception('Number of tokens and tags is not the same.'))

	return token_list, tag_list

@timeit		
def lists_to_spacy(tokens,tags,nlp):
	"""Creates a new spacy object from token and tag lists, and executes parsing algorithms"""
	if not len(tokens) == len(tags):
		raise(Exception('Number of tokens and tags is not the same.'))
		return
	
	try:
		doc = nlp.tokenizer.tokens_from_list(tokens)
		nlp.tagger.tag_from_strings(doc,tags)
		nlp.parser(doc)
		return doc
	except (AssertionError, IndexError) as e:
		print("Error while creating spacy object for the sentence '{}'.".format(" ".join(tokens)))
		print(e)
		return

@timeit	
def spacy_to_json(doc,text=False):
	"""Given a spaCy doc object, produce PubAnnotate JSON, that can be read by TextAE
	   If original text is provided, original positions will be computed"""
	
	pre_json = { "text" : text }
	pre_json["denotations"] = list()
	pre_json["relations"] = list()
	
	current_position = 0
	for token in doc:
		token_dict = dict()
		token_dict["id"] = "T{}".format(token.i)
		
		if text:
			position = text[current_position:].find(token.text)
			
			# token not found
			if position == -1:
				verbose("Token {} could not be found when realigning spaCy with original text.".format(token.text))
				verbose("The following text except was searched: {} (starting from position {})".format(text[current_position:],current_position))
				continue
				
			token_dict["span"] = { "begin" : current_position + position , "end" : current_position + position + len(token.text)}
			current_position += position + len(token.text)
		else:
			token_dict["span"] = { "begin" : token.idx , "end" : token.idx + len(token)}
			
		token_dict["obj"] = token.tag_
		pre_json["denotations"].append(token_dict)
	
		relation_dict = dict()
		relation_dict["id"] = "R{}".format(token.i)
		relation_dict["subj"] = "T{}".format(token.i)
		relation_dict["obj"] = "T{}".format(token.head.i)
		relation_dict["pred"] = token.dep_
		pre_json["relations"].append(relation_dict)
	
	my_json = json.loads(json.dumps(pre_json))
	return(json.dumps(my_json,sort_keys=True))

################
# RUN THE SCRIPT
################
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-m', '--model' , action="store" ,
						dest="model" , default=STANFORD_MODEL ,
						help="Complete path to Stanford model")
	parser.add_argument('-s', '--separator' , action="store" ,
						dest="separator" , default=STANFORD_SEPARATOR ,
						help="Character used by Stanford tagger to display separation between tag and token, normally example_NN or example/NN")
	parser.add_argument('-v','--verbose' , action="store_true" ,
						dest="verbose" , default=False ,
						help="Activates loading and debug messages")
	arguments = parser.parse_args(sys.argv[1:])
	
	STANFORD_MODEL = arguments.model
	STANFORD_SEPARATOR = arguments.separator
	
	start = verbose("Stanford + spaCy accessor.")
		
	# in python, if-statements do not introduce a new scope
	# so these variables are globally available
	verbose("Loading spaCy (this can easily take some 20 seconds)...")
	s = time.time()
	
	# for faster testing
	SPACY = English()
	verbose("Loaded spaCy in {:2.3f} seconds.".format(time.time()-s))
	verbose("Stanford + spaCy accessor loaded completely.")
	
	verbose("Launching Flask server now...")
	# Change this debug=False when deployed.
	# Otherwise any python code can be run on server
	app.run(debug=True)
	
	
