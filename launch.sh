#!/bin/bash

# is tmux installed
tmux_installed=$(which tmux | wc -l)

#########
# NO TMUX
#########
if [ $tmux_installed -eq 0 ];
then
	echo "tmux not installed. will launch processes in current shell."
	
	# Check if Java process already running
	java_process=$(ps -ef | grep "java -mx1000m -cp stanford-postagger.jar:lib/\* edu.stanford.nlp.tagger.maxent.MaxentTaggerServer -model models/wsj-0-18-left3words-nodistsim.tagger -port 2020" | grep -v "grep" | wc -l )
	if [ $java_process -eq 1 ];
	then
		echo "Java process already running"
	else
		cd stanford
		java -mx1000m -cp stanford-postagger.jar:lib/* edu.stanford.nlp.tagger.maxent.MaxentTaggerServer -model models/wsj-0-18-left3words-nodistsim.tagger -port 2020 > /dev/null 2>&1 &
		cd ..
	fi
	
	echo "Launching python process"
	python3 accessor.py $1

####################
# EVERYTHING IN TMUX
####################
else
	echo "Opening tmux session"
	tmux new -d -s 'Stanford + spaCy accessor'
	
	# Check if process already running
	java_process=$(ps -ef | grep "java -mx1000m -cp stanford-postagger.jar:lib/\* edu.stanford.nlp.tagger.maxent.MaxentTaggerServer -model models/wsj-0-18-left3words-nodistsim.tagger -port 2020" | grep -v "grep" | wc -l )
	if [ $java_process -eq 1 ];
	then
		echo "Java process already running"
	else
		tmux send -t 'Stanford + spaCy accessor' "cd stanford" Enter
		tmux send -t 'Stanford + spaCy accessor' "java -mx1000m -cp stanford-postagger.jar:lib/* edu.stanford.nlp.tagger.maxent.MaxentTaggerServer -model models/wsj-0-18-left3words-nodistsim.tagger -port 2020 > /dev/null 2>&1 &" Enter
		tmux send -t 'Stanford + spaCy accessor' "cd .." Enter
	fi
	
	tmux send -t 'Stanford + spaCy accessor' "python3 accessor.py" Enter
	
	# Detach
	tmux send -t 'Stanford + spaCy accessor' "python3 accessor.py" C-b  d
	
	echo "ready to rumble. Use \"tmux attach -t 'Stanford + spaCy accessor'\""{'denotations': [{'id': 'T0', 'obj': 'JJ', 'span': {'begin': 0, 'end': 4}}, {'id': 'T1', 'obj': 'PRP', 'span': {'begin': 5, 'end': 6}}, {'id': 'T2', 'obj': 'VBD', 'span': {'begin': 7, 'end': 15}}, {'id': 'T3', 'obj': 'DT', 'span': {'begin': 16, 'end': 20}}, {'id': 'T4', 'obj': 'JJ', 'span': {'begin': 21, 'end': 29}}, {'id': 'T5', 'obj': 'NN', 'span': {'begin': 30, 'end': 34}}, {'id': 'T6', 'obj': 'TO', 'span': {'begin': 35, 'end': 37}}, {'id': 'T7', 'obj': 'VB', 'span': {'begin': 38, 'end': 42}}, {'id': 'T8', 'obj': 'NN', 'span': {'begin': 43, 'end': 52}}, {'id': 'T9', 'obj': 'IN', 'span': {'begin': 53, 'end': 55}}, {'id': 'T10', 'obj': 'RB', 'span': {'begin': 56, 'end': 63}}, {'id': 'T11', 'obj': '.', 'span': {'begin': 63, 'end': 64}}], 'text': 'Much I marveled this ungainly fowl to hear discourse so plainly.', 'relations': [{'subj': 'T0', 'pred': 'advmod', 'id': 'R0', 'obj': 'T2'}, {'subj': 'T1', 'pred': 'nsubj', 'id': 'R1', 'obj': 'T2'}, {'subj': 'T2', 'pred': 'ROOT', 'id': 'R2', 'obj': 'T2'}, {'subj': 'T3', 'pred': 'det', 'id': 'R3', 'obj': 'T5'}, {'subj': 'T4', 'pred': 'amod', 'id': 'R4', 'obj': 'T5'}, {'subj': 'T5', 'pred': 'dobj', 'id': 'R5', 'obj': 'T2'}, {'subj': 'T6', 'pred': 'aux', 'id': 'R6', 'obj': 'T7'}, {'subj': 'T7', 'pred': 'advcl', 'id': 'R7', 'obj': 'T2'}, {'subj': 'T8', 'pred': 'dobj', 'id': 'R8', 'obj': 'T7'}, {'subj': 'T9', 'pred': 'advmod', 'id': 'R9', 'obj': 'T10'}, {'subj': 'T10', 'pred': 'advmod', 'id': 'R10', 'obj': 'T7'}, {'subj': 'T11', 'pred': 'punct', 'id': 'R11', 'obj': 'T2'}]}" to see session."
fi

