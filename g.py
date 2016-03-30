#from flask import Flask, request, jsonify
# from spacy.en import English

import argparse , sys
import json
import subprocess

# 1: use Flask to give text to parse
# 2.1: use spacy to parse
# 2.2: include stanford pos
# 3: return PB Json (which can be visualized in TextAE)

def pubannotation(input_text,nlp):
	pre_json = { "text" : input_text }
	pre_json["denotations"] = list()
	pre_json["relations"] = list()
	
	for token in nlp(input_text):
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

def stanford():
	subprocess.call(['ls', '-l'])
	
		
# 
# app = Flask(__name__)
# nlp = English()
# 
# @app.route('/')
# def welcome():
#     return('Hello there')
#     
# @app.route('/parse')
# def parse():
#     if 'text' in request.args:
#         text_ = request.args['text']
#         doc = nlp(text_)
#         resp = jsonify(text_)
#         resp.status_code = 200
#         return(resp)
#     else:
#         return(None)
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('input_text', action="store")
	arguments = parser.parse_args(sys.argv[1:])
	
	
	
	pb = pubannotation(arguments.input_text)
	print(pb)
	
	
#	app.run(debug=True)