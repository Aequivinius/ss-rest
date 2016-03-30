
import java.io.BufferedReader;
import java.io.FileReader;
import java.util.List;
import java.io.*;

import edu.stanford.nlp.ling.Sentence;
import edu.stanford.nlp.ling.TaggedWord;
import edu.stanford.nlp.ling.HasWord;
import edu.stanford.nlp.tagger.maxent.MaxentTagger;
import edu.stanford.nlp.tagger.maxent.TaggerConfig;

class Tagger {

  private Tagger() {}

  public static void main(String[] args) throws Exception {
    if (args.length != 2) {
      System.err.println("usage: java Tagger modelFile stringToTag");
      return;
    }
    
    MaxentTagger tagger = new MaxentTagger(args[0]);
    
    // String taggedString = tagger.tagString(args[1]);
    List<List<HasWord>> sentences = MaxentTagger.tokenizeText(new BufferedReader(new StringReader(args[1])));
        for (List<HasWord> sentence : sentences) {
          List<TaggedWord> tSentence = tagger.tagSentence(sentence);
          for (TaggedWord t : tSentence) {
            System.out.println(t);
          }
          String s = Sentence.listToString(tSentence, false);
 //         System.out.println(s+"\n");
        } 
    // System.out.println(taggedString);
    }
}
