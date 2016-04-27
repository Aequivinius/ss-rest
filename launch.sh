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
	
	echo "ready to rumble. Use 'tmux attach -t 'Stanford + spaCy accessor' to see session."
fi

