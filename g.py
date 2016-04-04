from flask import Flask, request, jsonify , make_response , render_template
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

test_string = """{"denotations": [{"id": "T0", "obj": "NNP", "span": {"begin": 0, "end": 9}}, {"id": "T1", "obj": "IN", "span": {"begin": 10, "end": 12}}, {"id": "T2", "obj": "NN", "span": {"begin": 13, "end": 23}}, {"id": "T3", "obj": "NN", "span": {"begin": 24, "end": 31}}, {"id": "T4", "obj": "IN", "span": {"begin": 32, "end": 34}}, {"id": "T5", "obj": "NNP", "span": {"begin": 35, "end": 47}}, {"id": "T6", "obj": "IN", "span": {"begin": 48, "end": 51}}, {"id": "T7", "obj": "NN", "span": {"begin": 52, "end": 56}}, {"id": "T8", "obj": "NN", "span": {"begin": 57, "end": 64}}, {"id": "T9", "obj": "IN", "span": {"begin": 65, "end": 67}}, {"id": "T10", "obj": "IN", "span": {"begin": 68, "end": 70}}, {"id": "T11", "obj": "NN", "span": {"begin": 71, "end": 75}}, {"id": "T12", "obj": "NN", "span": {"begin": 76, "end": 89}}, {"id": "T13", "obj": ".", "span": {"begin": 90, "end": 91}}], "relations": [{"id": "R0", "obj": "T0", "pred": "ROOT", "subj": "T0"}, {"id": "R1", "obj": "T0", "pred": "prep", "subj": "T1"}, {"id": "R2", "obj": "T3", "pred": "compound", "subj": "T2"}, {"id": "R3", "obj": "T1", "pred": "pobj", "subj": "T3"}, {"id": "R4", "obj": "T3", "pred": "prep", "subj": "T4"}, {"id": "R5", "obj": "T4", "pred": "pobj", "subj": "T5"}, {"id": "R6", "obj": "T3", "pred": "prep", "subj": "T6"}, {"id": "R7", "obj": "T8", "pred": "compound", "subj": "T7"}, {"id": "R8", "obj": "T6", "pred": "pobj", "subj": "T8"}, {"id": "R9", "obj": "T0", "pred": "prep", "subj": "T9"}, {"id": "R10", "obj": "T0", "pred": "prep", "subj": "T10"}, {"id": "R11", "obj": "T12", "pred": "amod", "subj": "T11"}, {"id": "R12", "obj": "T10", "pred": "pobj", "subj": "T12"}, {"id": "R13", "obj": "T0", "pred": "punct", "subj": "T13"}], "text": "Induction of chromosome banding by trypsin/EDTA for gene mapping by in situ hybridization ."}"""

##############
# FLASK THINGS
##############
@app.route('/spacy_rest', methods = ['GET', 'POST'])
def rest():
	"""Used to make requests as:
	   curl 127.0.0.1:5000/spacy_rest?text=This+is+a+test
	"""
	
	if request.method == 'GET':
		if 'text' in request.args:
			json_ = text_to_json(request.args['text'])
			return(render_template('readme.html',labat=json_,labut=request.args['text']))
		return(render_template('readme.html',labut="It is a REST service to produce annotation of syntactic parsing."))
		
	if request.method == 'POST':
		if 'text' in request.form:
			return(text_to_response(request.args['text']))

@app.route('/spacy_rest/' , methods = ['GET','POST'])
def rest_d():
	"""Make requests using curl -d, giving a 'text' to the request"""

	if request.headers['Content-Type'] == 'application/json':
		
		if 'text' in request.get_json():
			return(text_to_response(request.get_json()['text']))
		else:
			return("400 Bad Request (no 'text' data)")
	elif request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
		if 'text' in request.form:
			return(text_to_response(request.form['text']))
		else:
			return("400 Bad Request (no 'text' data)")
	else:
		return("415 Unsupported media type\n")	

def text_to_response(text):
	json = text_to_json(text)
	response = json_to_response(json)
	return response
		
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
		json_ = spacy_to_pubannotation(doc)
		return(json_)
	except():
		return('400 Bad Request (possibly an error occured when parsing due to unexpected format')

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
