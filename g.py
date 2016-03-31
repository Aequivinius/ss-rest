from flask import Flask, request, jsonify
from spacy.en import English
import pexpect

import subprocess
import argparse , sys
import json
import os.path

# Global variables to match the model and mode used by stanford tagger
DEFAULT_MODEL = 'models/wsj-0-18-left3words-nodistsim.tagger'
DEFAULT_SEPARATOR = '/'
DEFAULT_STANFORD_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)),'stanford')

app = Flask(__name__)

# 1: use Flask to give text to parse
# 2.1: use stanford to tag
# 2.2: use spacy to parse
# 3: return PB Json (which can be visualized in TextAE)

##############
# FLASK THINGS
##############
@app.route('/spacy_rest', methods = ['GET','POST'])
def rest():
	"""Used to make requests as:
	   curl 127.0.0.1:5000/spacy_rest?text=This+is+a+test
	"""

	if 'text' in request.args:
		return(text_to_json(request.args['text']))

@app.route('/spacy_rest/' , methods = ['GET','POST'])
def rest_d():
	"""Make requests using curl -d, giving a 'text' to the request"""

	if request.headers['Content-Type'] == 'application/json':
		
		if 'text' in request.get_json():
			return(text_to_json(request.get_json()['text']))
		else:
			return("400 Bad Request (no 'text' data)")
	elif request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
		if 'text' in request.form:
			return(text_to_json(request.form['text']))
		else:
			return("400 Bad Request (no 'text' data)")
	else:
		return("415 Unsupported media type\n")	
		
def text_to_json(text):
	"""Coordinates the entire pipeline"""
	
	global my_stanford
	global my_nlp
	try: 
		tokens = ask_stanford(my_stanford,text)
		print(tokens)
		tokens, tags = stanford_to_lists(tokens)
		print(tokens,tags)
		doc = lists_to_spacy(tokens,tags,my_nlp)
		print(doc)
		json = spacy_to_pubannotation(doc)
		return(json)
	except():
		return('400 Bad Request (possibly an error occured when parsing due to unexpected format')

#################
# ACTUAL PIPELINE
#################v

def stanford_pexpect(model=DEFAULT_MODEL,separator=DEFAULT_SEPARATOR,stanford=DEFAULT_STANFORD_DIRECTORY):
	"""Uses pexpect to launch a Stanford JVM, which can be used repeatedly using ask_stanford() to tag text. """

	# Explanations of arguments can be found here
	# http://www-nlp.stanford.edu/nlp/javadoc/javanlp/edu/stanford/nlp/tagger/maxent/MaxentTagger.html
	
	child = pexpect.spawnu("java -cp '.:stanford-postagger.jar:lib/*' TaggerConsole {0}".format(model),cwd=stanford, maxread=1)
	child.expect("STFINPT:",timeout=5)

	return child	
	
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

my_stanford = stanford_pexpect()
my_nlp = English()

if __name__ == '__main__':
	# parser = argparse.ArgumentParser()
	# parser.add_argument('-m', '--model' , action="store" ,
	# 					dest="model" , default=DEFAULT_MODEL)
	# arguments = parser.parse_args(sys.argv[1:])
		
	app.run(debug=True)
