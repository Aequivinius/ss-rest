from flask import Flask, request, jsonify
from spacy.en import English

import argparse , sys
import json
import subprocess
import pexpect

# Global variables to match the model and mode used by stanford tagger
DEFAULT_MODEL = 'models/wsj-0-18-left3words-nodistsim.tagger'
DEFAULT_SEPARATOR = '/'

app = Flask(__name__)
nlp = English()

# 1: use Flask to give text to parse
# 2.1: use stanford to tag
# 2.2: use spacy to parse
# 3: return PB Json (which can be visualized in TextAE)

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

def stanford(input_text,model=DEFAULT_MODEL):
	"""Uses model to tokenize and tag input text. Assumes Stanford POS tagger is in 'stanford' subdirectory, and that Tagger.java is already compiled."""

	subprocess.call(['pwd'])
	output = subprocess.check_output([	'java', 
						'-cp',
						'.:stanford-postagger.jar:lib/*',
						'Tagger',
						model,
						input_text
						], cwd='stanford'
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
			token_list.append("".join(token.split(separator)[:-1]))
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
		return None


def text_to_json(textus):
	lista = stanford(textus)
	print(lista)
	tokens, tags = stanford_to_lists(lista,'/')
	print(tokens, tags)
	doc = lists_to_spacy(tokens,tags,nlp)
	print(doc)
	json = spacy_to_pubannotation(doc)
	return(json)

@app.route('/spacy_rest', methods = ['GET','POST'])
def spacy_rest():
	
	if 'text' in request.args:
		return(text_to_json(request.args['text']))
	
@app.route('/spacy_rest/' , methods = ['GET','POST'])
def spacy_rest_d():
	
	if request.headers['Content-Type'] == 'application/json':
		return(text_to_json(request.get_json()['text']))
	elif request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
		
		return(text_to_json(request.form['text']))
	else:
		return("415 Unsupported media type\n")	

def expection():
	child = pexpect.spawnu('java -mx300m -classpath stanford-postagger.jar:lib/* edu.stanford.nlp.tagger.maxent.MaxentTagger -model models/wsj-0-18-bidirectional-distsim.tagger',cwd='stanford')
	child.expect('.*\)')

if __name__ == '__main__':
	# parser = argparse.ArgumentParser()
	# parser.add_argument('-m', '--model' , action="store" ,
	# 					dest="model" , default=DEFAULT_MODEL)
	# arguments = parser.parse_args(sys.argv[1:])
	
	app.run(debug=True)
	
	# expection()
