from flask import Flask, request , make_response , render_template
from spacy.en import English
import pexpect

import subprocess
import argparse , sys
import json
import os.path
import time

# Default values to match the model and mode used by stanford tagger
DEFAULT_MODEL = 'models/wsj-0-18-left3words-nodistsim.tagger'
DEFAULT_SEPARATOR = '/'
DEFAULT_STANFORD_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)),'stanford')

TEXT_ERROR = "No 'text' to process. Use spacy_rest?text=This+is+an+example."
DEFAULT_TEST_INPUT = "It is a REST service to produce annotation of syntactic parsing."
TEST_JSON = """{
  "text": "It is a REST service to produce annotation of syntactic parsing.",
  "denotations": [
	{
	  "id": "T0",
	  "span": {
		"begin": 0,
		"end": 2
	  },
	  "obj": "PRP"
	},
	{
	  "id": "T1",
	  "span": {
		"begin": 3,
		"end": 5
	  },
	  "obj": "VB"
	},
	{
	  "id": "T2",
	  "span": {
		"begin": 6,
		"end": 7
	  },
	  "obj": "DT"
	},
	{
	  "id": "T3",
	  "span": {
		"begin": 8,
		"end": 12
	  },
	  "obj": "NN"
	},
	{
	  "id": "T4",
	  "span": {
		"begin": 13,
		"end": 20
	  },
	  "obj": "NN"
	},
	{
	  "id": "T5",
	  "span": {
		"begin": 21,
		"end": 23
	  },
	  "obj": "TO"
	},
	{
	  "id": "T6",
	  "span": {
		"begin": 24,
		"end": 31
	  },
	  "obj": "VB"
	},
	{
	  "id": "T7",
	  "span": {
		"begin": 32,
		"end": 42
	  },
	  "obj": "NN"
	},
	{
	  "id": "T8",
	  "span": {
		"begin": 43,
		"end": 45
	  },
	  "obj": "IN"
	},
	{
	  "id": "T9",
	  "span": {
		"begin": 46,
		"end": 55
	  },
	  "obj": "JJ"
	},
	{
	  "id": "T10",
	  "span": {
		"begin": 56,
		"end": 63
	  },
	  "obj": "NN"
	}
  ],
  "relations": [
	{
	  "id": "R0",
	  "subj": "T6",
	  "obj": "T0",
	  "pred": "arg1Of"
	},
	{
	  "id": "R1",
	  "subj": "T6",
	  "obj": "T1",
	  "pred": "arg1Of"
	},
	{
	  "id": "R2",
	  "subj": "T4",
	  "obj": "T1",
	  "pred": "arg2Of"
	},
	{
	  "id": "R3",
	  "subj": "T4",
	  "obj": "T2",
	  "pred": "arg1Of"
	},
	{
	  "id": "R4",
	  "subj": "T4",
	  "obj": "T3",
	  "pred": "arg1Of"
	},
	{
	  "id": "R5",
	  "subj": "T6",
	  "obj": "T5",
	  "pred": "arg1Of"
	},
	{
	  "id": "R6",
	  "subj": "T7",
	  "obj": "T6",
	  "pred": "arg2Of"
	},
	{
	  "id": "R7",
	  "subj": "T7",
	  "obj": "T8",
	  "pred": "arg1Of"
	},
	{
	  "id": "R8",
	  "subj": "T10",
	  "obj": "T8",
	  "pred": "arg2Of"
	},
	{
	  "id": "R9",
	  "subj": "T10",
	  "obj": "T9",
	  "pred": "arg1Of"
	}
  ]
}
"""

app = Flask(__name__)

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
	"""Used to make requests as:
	   curl 127.0.0.1:5000/spacy_rest?text=This+is+a+test
	and to serve the HTML"""
	
	# serve plain JSON. 'text' can hide either in request.args or request.form
	if 'curl' in request.headers['User-Agent'].lower() or request.method == 'POST':
		verbose("Received request from cURL. Will return JSON...")
		if 'text' in request.args and request.args['text'] is not '':
			try:
				return(text_to_response(request.args['text']))
			except Exception:
				return(error_page("Error while processing request for '{}'.".format(request.args['text'])),500)
		if 'text' in request.form and request.form['text'] is not '':
			try:
				return(text_to_response(request.form['text']))
			except Exception:
				return(error_page("Error while processing request for '{}'.".format(request.form['text'])),500)
		
		# some other fantasy argument supplied
		if len(request.args) > 0:
			return(TEXT_ERROR,400)
		
		return(TEXT_ERROR,400)
	
	# serve HTML
	if request.method == 'GET':
		if 'text' in request.args and request.args['text'] is not '':
			verbose("Received GET request for '{}'. Will return HTML...".format(request.args['text']))
			try:
				json_ = text_to_json(request.args['text'])
				pretty_json = json.dumps(json.loads(json_),sort_keys=True,indent=4)
				return(render_template('index.html',json=json_,pretty_json=pretty_json,input_text=request.args['text']))
			except Exception:
				return(error_page("Error processing GET request for '{}'".format(request.args['text'])),500)
		
		# some other fantasy argument supplied
		if len(request.args) > 0:
			return(error_page(TEXT_ERROR),400)
	
	return(render_template('index.html',input_text=DEFAULT_TEST_INPUT),300)

@app.route('/spacy_rest/' , methods = ['GET','POST'])
def rest_d():
	"""Make requests using curl -d, giving a 'text' to the request."""

	if request.headers['Content-Type'] == 'application/json':
		if 'text' in request.get_json():
			try:
				return(text_to_response(request.get_json()['text']))
			except Exception as e:
				return("Error processing request for '{}'.\n{}".format(request.get_json()['text'],e),500)
		return(TEXT_ERROR,400)
	
	if request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
		if 'text' in request.form:
			try:
				return(text_to_response(request.form['text']))
			except Exception as e:
				return("Error processing request for '{}'.\n{}".format(request.form['text'],e),500)
		else:
			return(TEXT_ERROR,400)
	else:
		return("Unsupported media type.",415)
		
def error_page(error):
	return(render_template('index.html',error=error,input_text=DEFAULT_TEST_INPUT))
	
@app.errorhandler(404)
def not_found(error):
	return(render_template('index.html',error="404 Page not found",page_not_found="true"))

def text_to_response(text):
	"""Coordinates the entire pipeline. Returns a Response containing JSON."""
	json_ = text_to_json(text)
	response = json_to_response(json_)
	return response
		
def text_to_json(text):
	"""Coordinates the entire pipeline"""
	
	try: 
		tokens = ask_stanford(STANFORD,text)
		print(tokens)
		tokens, tags = stanford_to_lists(tokens)
		print(tokens,tags)
		doc = lists_to_spacy(tokens,tags,SPACY)
		print(doc)
		json_ = spacy_to_pubannotation(doc)
		return(json_)
	except Exception:
		return('400 Bad Request (possibly an error occured when parsing due to unexpected format',400)

def json_to_response(json_):
	response = make_response(json_)
	
	# This is necessary to allow the REST be accessed from other domains
	response.headers['Access-Control-Allow-Origin'] = '*'
	return(response)
	

#################
# ACTUAL PIPELINE
#################v
def stanford_pexpect(model=DEFAULT_MODEL,separator=DEFAULT_SEPARATOR,stanford=DEFAULT_STANFORD_DIRECTORY):
	"""Uses pexpect to launch a Stanford JVM, which can be used repeatedly using ask_stanford() to tag text. """

	# Explanations of arguments can be found here
	# http://www-nlp.stanford.edu/nlp/javadoc/javanlp/edu/stanford/nlp/tagger/maxent/MaxentTagger.html
	
	child = pexpect.spawnu("java -cp '.:stanford-postagger.jar:lib/*' TaggerConsole {0}".format(model),cwd=stanford, maxread=1)
	child.expect("STFINPT:",timeout=5)
	return(child)
	
def ask_stanford(stanford,text):
	"""Tags text using a previously created Stanford JVM using stanford_pexpect()"""
	
	stanford.sendline(text)
	stanford.expect('STFINPT:')

	# This is necessary because pipe is not properly flushed
	# https://pexpect.readthedocs.org/en/stable/commonissues.html
	result = stanford.before + stanford.after

	tokens = result.splitlines()[1:-1]
	return(tokens)

def stanford(input_text,model=DEFAULT_MODEL,stanford=DEFAULT_STANFORD_DIRECTORY):
	"""Uses model to tokenize and tag input text. Assumes that Tagger.java is already compiled. This method creates and closes a new JVM for every call."""

	subprocess.call(['pwd'])
	output = subprocess.check_output([	'java', 
						'-cp',
						'.:stanford-postagger.jar:lib/*',
						'Tagger',
						model,
						input_text
						], cwd=stanford
						)

	return([s.decode("utf-8").strip() for s in output.splitlines()])

def stanford_to_lists(tokens,separator=DEFAULT_SEPARATOR):
	"""Extracts tags and tokens from Stanfords representation. Different models use different separators, usually '/' or '_'"""
	token_list = list()
	pos_list = list()

	for token in tokens:

		# SPECIAL CASE
		# -LBR- and -RRB- from Stanford tagger must be 
		# replaced by actual parentheses for spaCy parser
		if "".join(token.split(separator)[:-1]) == '-LRB-':
			token_list.append("(")

		elif "".join(token.split(separator)[:-1]) == '-RRB-':
			token_list.append(")")

		else:
			token_list.append(separator.join(token.split(separator)[:-1]))
		pos_list.append(token.split(separator)[-1])

	return token_list, pos_list
		
def lists_to_spacy(tokens,tags,nlp):
	"""Creates a new spacy object from token and tag lists, and executes parsing algorithms"""
	try:
		doc = nlp.tokenizer.tokens_from_list(tokens)
		nlp.tagger.tag_from_strings(doc,tags)
		nlp.parser(doc)
		return doc
	except (AssertionError, IndexError) as e:
		print("Error while creating spacy object for the sentence '{}'.".format(" ".join(tokens)))
		print(e)
		return None
		
def spacy_to_pubannotation(doc):
	"""Given a spaCy doc object, produce PubAnnotate JSON, that can be read by TextAE, for example"""
	pre_json = { "text" : doc.text }
	pre_json["denotations"] = list()
	pre_json["relations"] = list()

	for token in doc:
		token_dict = dict()
		token_dict["id"] = "T{}".format(token.i)
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

#########################
# SCRIPT HELPER FUNCTIONS
#########################
def verbose(text):
	if arguments.verbose:
		print(text)
		return time.time()
	return 0

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-m', '--model' , action="store" ,
						dest="model" , default=DEFAULT_MODEL ,
						help="Complete path to Stanford model")
	parser.add_argument('-s', '--separator' , action="store" ,
						dest="separator" , default=DEFAULT_SEPARATOR ,
						help="Character used by Stanford tagger to display separation between tag and token, normally example_NN or example/NN")
	parser.add_argument('--stanford' , action="store" ,
						dest="stanford" , default=DEFAULT_STANFORD_DIRECTORY ,
						help="Complete path to directory containing stanford-postagger.jar, lib folder and TaggerConsole.class")
	parser.add_argument('-v','--verbose' , action="store_true" ,
						dest="verbose" , default=False ,
						help="Activates loading and debug messages")					
	arguments = parser.parse_args(sys.argv[1:])
	
	DEFAULT_MODEL = arguments.model
	DEFAULT_SEPARATOR = arguments.separator
	DEFAULT_STANFORD_DIRECTORY = arguments.stanford
	
	start = verbose("Stanford + spaCy accessor.\n")
		
	# in python, if statements do not introduce a new scope
	# so these variables are globally available
	start = verbose("Launching Stanford JVM...")
	STANFORD = stanford_pexpect()
	verbose("Stanford JVM launched after {:.3f} seconds.\n".format(time.time()-start))
	
	start = verbose("Loading spaCy (this can easily take some 20 seconds)...")
	SPACY = English()
	verbose("Loaded spaCy in {:.3f} seconds.\n".format(time.time()-start))
	
	verbose("Launching Flask server now...")
	# Change this debug=False as soon as deployed.
	# Otherwise any python code can be run on server
	app.run(debug=arguments.verbose)
	
	verbose("Stanford + spaCy accessor loaded completely.\n")
