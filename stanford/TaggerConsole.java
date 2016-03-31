
import java.io.BufferedReader;
import java.io.FileReader;
import java.util.List;
import java.util.Scanner;
import java.io.*;

import edu.stanford.nlp.ling.Sentence;
import edu.stanford.nlp.ling.TaggedWord;
import edu.stanford.nlp.ling.HasWord;
import edu.stanford.nlp.tagger.maxent.MaxentTagger;
import edu.stanford.nlp.tagger.maxent.TaggerConfig;

class TaggerConsole {

  private TaggerConsole() {}

  public static void main(String[] args) throws Exception {
    if (args.length != 1) {
      System.err.println("usage: java Tagger modelFile");
      return;
    }
    
    MaxentTagger tagger = new MaxentTagger(args[0]);
    
    Scanner reader = new Scanner(System.in);
    
    while (true) {
      String in = System.console().readLine("STFINPT:");
      
      List<List<HasWord>> sentences = MaxentTagger.tokenizeText(new BufferedReader(new StringReader(in)));
      for (List<HasWord> sentence : sentences) {
        List<TaggedWord> tSentence = tagger.tagSentence(sentence);
        for (TaggedWord t : tSentence) {
          System.out.println(t);
        }
      }
    }
  }
}
