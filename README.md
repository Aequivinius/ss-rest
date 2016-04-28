# Stanford + spaCy accessor
A RESTful web service for parsing.

## Usage
Once deployed, the web service can be accessed in two ways:
* via the self-explanatory website
* via the API, using [cURL](https://curl.haxx.se/), for example.

The RESTful API can be accessed using HTML POST requests, providing the text to be parsed as a 'text' argument. The service will return [PubAnnotation JSON](http://www.pubannotation.org/docs/annotation-format/). 

`curl -H "content-type:application/json" -d '{"text":"This is a sample sentence."}' 127.0.0.1:5000/spacy_rest/`

`curl -d text="Induction of chromosome banding by trypsin/EDTA for gene mapping by in situ hybridization." 127.0.0.1:5000/spacy_rest/`

Replace the server address 127.0.0.1:5000 above by the address of the server hosting the service, once deployed.

Any other service making RESTful requests should be possible to use. In particular, this web service was developed in order to be used in conjunction with [PubAnnotation](http://pubannotation.org/), which allows users to obtain annotations for collections of biomedical text automatically, and align them with the original publication.

## Parsing
A combination of the famous [Stanford POS tagger](http://nlp.stanford.edu/software/tagger.shtml) and [spaCy](https://spacy.io/) for parsing is used. 

spaCy is a python library for NLP. It's main strength is it's speed, owing to the underlying implementation in cython. While it does offer tokenization and POS tagging, we found that the tagger does not perform well, especially in the biomedical domain.

We thus employ Stanford tagger in conjunction with spaCy's parser to provide high accuracy and speed.

## Implementation
The Stanford POS tagger is written in Java, and can be run as a server using [java.net.ServerSocket](https://docs.oracle.com/javase/7/docs/api/java/net/ServerSocket.html). Using sockets proved to be an easy way to communicate between python and Java reliably.

The accessor.py uses [Flask](http://flask.pocoo.org/) to launch a web service listening to *rest_spacy* and *rest_spacy/* for incoming requests. Since loading spaCy models takes a considerable amount of time, one object containing these models is maintained that is then used for all requests.

For every request, a new client socket for the Stanford server socket is created, and Stanford's reply is read. The tokenized and tagged text is then passed to the spaCy object. The parses provided by spaCy are then realigned with the original text to facilitate using the results in [PubAnnotation](http://pubannotation.org/), converted into JSON and returned to the client.

## Performance
Informal evaluation shows that the time for each request grows linearly in size, taking roughly 0.1s per 1000 characters. A more formal evaluation of the parsing quality can be found [here](http://cs.aequivinius.ch/downloads/dependencyparsing.pdf).

## Launching server
The script *launch.sh* takes care of launching both the Stanford server and the accessor.py. If *tmux* is installed, it will try to launch these process in a new tmux session so that the shell can be closed without stopping the processes necessary for the server. Run the script as follows:

`./launch.sh` or `./launch.sh -v`

Alternatively, you can start the processes manually. From the *stanford* directory, the server can be launched as follows:

`java -mx1000m -cp stanford-postagger.jar:lib/* edu.stanford.nlp.tagger.maxent.MaxentTaggerServer -model models/wsj-0-18-left3words-nodistsim.tagger -port 2020 -tokenizerOptions "strictTreebank3=true" &`

This will launch a server socket on port 2020, which can only be accessed from the same machine. 

The argument *strictTreebank3=true* is necessary to change the default behaviour of [Stanford tokenizer](http://nlp.stanford.edu/nlp/javadoc/javanlp/edu/stanford/nlp/process/PTBTokenizer.html), which adds a spurious dot if a sentence ends in an abbreviation ending in a dot. While this is useful for parsing, this behaviour makes hinders subsequent realignment with the original text.

The accessor.py is then launched using the following command, which optionally takes the `-v` or `--verbose` argument to display more information when processing requests.

`python3 accessor.py`

Note that for deployment, the last line must be changed.

`app.run(debug=True)`

The `debug=False` *must* be set to prevent arbitrary code from being possible to be executed on the server. Furthermore, `host='0.0.0.0` should be set in order for the service to be accessible, as well as `port` be set to the respective port.

## Project
The project currently is fully operational, and no major changes to the underlying workings is to be expected.
