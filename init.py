from flask import Flask, render_template, request
import re, os
from afinn import Afinn
from wordBreak import wordBreak

app = Flask(__name__)

# Global base directory for accessing local resources like .txt files
BASEDIR = os.path.dirname(__file__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/review', methods=['POST'])
def review():
    txt = ""
    fileTxt = ""
    action = ""
    if request.method == 'POST':
        print("Form data:", request.form)
        action = request.form.get("action")
        txt = request.form.get('txt')
        file = request.files.get('filetxt')
        fileTxt = file.read().decode("utf-8") if file else ""
    
    afinn = Afinn()

    # -------------------------------
    # DATA PROCESSING: TEXT CLEANING
    # -------------------------------

    def splittingPara(paragraph):
        abbreviations = [
            "Mr", "Mrs", "Ms", "Dr", "Prof", "Sr", "Jr",
            "e.g", "i.e", "etc", "vs", "Fig", "fig", "approx"
        ]
        
        # Escape abbreviations for regex and join them with | for alternation
        abbrev_regex = r'\b(?:' + '|'.join([re.escape(abbrev) for abbrev in abbreviations]) + r')\.'
        
        # Temporarily replace abbreviations (with a special marker) to avoid splitting there
        temp_text = re.sub(abbrev_regex, lambda m: m.group(0).replace('.', '<ABBR_DOT>'), paragraph)
        
        # Now split on sentence-ending punctuation followed by space
        sentences = re.split(r'(?<=[.!?])\s+', temp_text.strip())
        
        # Put the dots back in abbreviations
        sentences = [s.replace('<ABBR_DOT>', '.') for s in sentences]
        
        return sentences
    
    def splittingNoSpace(paragraph):
        abbreviations = [
            "Mr", "Mrs", "Ms", "Dr", "Prof", "Sr", "Jr",
            "e.g", "i.e", "etc", "vs", "Fig", "fig", "approx"
        ]
        
        # Step 1: Replace all known abbreviations (with dot) with temp marker
        for abbr in abbreviations:
            # Match abbreviation followed by a dot, regardless of what comes before or after
            pattern = rf'(?<!\w)({re.escape(abbr)})\.(?!\w)'  # Dot not followed by word char
            paragraph = re.sub(pattern, r'\1<ABBR_DOT>', paragraph)

            # Also allow for abbreviation followed immediately by another capital word (like Mr.Costner)
            pattern_inline = rf'({re.escape(abbr)})\.(?=[A-Z])'
            paragraph = re.sub(pattern_inline, r'\1<ABBR_DOT>', paragraph)

        # Step 2: Split on sentence-ending punctuation followed by a capital letter or end of string
        sentences = re.split(r'(?<=[.!?])(?=[A-Z]|$)', paragraph.strip())

        # Step 3: Restore the abbreviation dots
        sentences = [s.replace('<ABBR_DOT>', '.').strip() for s in sentences if s.strip()]

        return sentences

    # -------------------------------
    # REQUIREMENT 1: CALCULATION OF SENTIMENT SCORE FOR EACH SENTENCE
    # -------------------------------
    def scoringSentence(sentences):
        #returns a list of tuples, each tuple has a sentence + score tied to each sentence
        #simply with just afinn.score
        negation_path = os.path.join(BASEDIR, "negations.txt")
        with open(negation_path, encoding="utf-8") as f:
            negations = set(line.strip().lower() for line in f if line.strip())

        scored_sentences = []

        for sentence in sentences:
            if sentence == ".":  # Skips empty sentences that are just a dot
                continue
            words = re.findall(r"\b\w+\b", sentence.lower())
            total_score = 0
            i = 0

            while i < len(words):
                word = words[i]
                score = afinn.score(word)

                # Check if the previous word is a negation
                if i > 0 and words[i-1] in negations and score != 0:
                    score *= -1  # Flip the sentiment
                total_score += score
                i += 1

            scored_sentences.append((sentence, total_score))

        return scored_sentences

    # -------------------------------
    # REQUIREMENT 2: MOST POSITIVE AND NEGATIVE SENTENCES
    # -------------------------------
    
    def findingExtremeScores(scored):
        if not scored:
            return (None,0), (None,0)
        
        #what i did previously:
        max_sentence = max(scored, key=lambda x: x[1])
        min_sentence = min(scored, key=lambda x: x[1])

        return max_sentence, min_sentence
    
    # -------------------------------
    # REQUIREMENT 5: CONTINUOUS SEGMENTS OF ARBITRARY LENGTH
    # -------------------------------
    def arbitrary_length(scored): 
    # Sliding window - fixed length, Kadane's algorithm finds segments of ANY length
    # Uses Big-O notation: O(n) - Time, O(1) Space      
        if not scored:
                return (None, 0), (None, 0)

        # Extract the just the numerical scores into a separate list 
        scores = [s[1] for s in scored]

        # Initialize var for tracking max & min subarray
        max_Sum = max_End = scores[0]                                  
        max_Result_Start = max_Result_End = max_Curr_Start = 0        # Start, End & Current Subarray (Max)
        min_Sum = min_End = scores[0]            
        min_Result_Start = min_Result_End = min_Curr_Start = 0     # Start, End & Current Subarray (Min)      

        # Go through the scores in list: start at index [1] 
        for i in range(1, len(scores)):
            # ---Most Pos segment---
            # If starting a new subarray from current element has a *smaller* sum than extending from previous subarray,
            if max_End + scores[i] > scores[i]:
                # Add current element to subarray sum
                max_End += scores[i]           
            else:
            # START AFRESH: Update current subarray sum with current element & start of subarray w index; stop extending previous segment
                max_End = scores[i]
                # Indicate where new segment starts
                max_Curr_Start = i             

            # If current subarray sum is greater than max subarray sum, Update to become most pos segment
            if max_End > max_Sum:
                # Update max subarray sum
                max_Sum = max(max_End,max_Sum)             
                max_Result_Start = max_Curr_Start          # Save where pos segment started
                max_Result_End = i                         # This is where pos segment ends

            #----Most Neg Segment----
            # If starting a new subarray from current element has a *greater* sum than extending from previous subarray,
            if min_End + scores[i] < scores[i]:        
                # Add current element to subarray sum
                min_End += scores[i]
            else:
                # START AFRESH: Update current subarray sum with current element & start of subarray w index; stop extending previous segment
                min_End = scores[i]
                min_Curr_Start = i
        
            # If current subarray sum is greater than min subarray sum, Update to become most neg segment
            if min_End < min_Sum:
                # Update min subarray sum
                min_Sum = min(min_End, min_Sum)           
                min_Result_Start = min_Curr_Start         # Save where neg segment started
                min_Result_End = i                        # This is where neg segment ends

        most_positive_segment = (scored[max_Result_Start:max_Result_End + 1], max_Sum)
        most_negative_segment = (scored[min_Result_Start:min_Result_End + 1], min_Sum)

        return most_positive_segment, most_negative_segment

    # -------------------------------
    # REQUIREMENT 4: FIXED SLIDING WINDOW OVER PARAGRAPHS
    # -------------------------------
    def SLIDINGWINDOW_EFFICIENT(scored, k):
        n = len(scored)
        if n < k:
            return None, None  # not enough sentences for one window

        # Start with the first 'k' sentences
        window_sum = sum(scored[i][1] for i in range(k))
        max_sum = min_sum = window_sum
        max_start = min_start = 0

        # Slide the window forward one sentence at a time
        for i in range(1, n - k + 1):
            # Add the new sentence at the end, subtract the old sentence at the start
            window_sum += scored[i+k-1][1] - scored[i-1][1]

            if window_sum > max_sum:  # found a new most positive window
                max_sum = window_sum
                max_start = i
            if window_sum < min_sum:  # found a new most negative window
                min_sum = window_sum
                min_start = i

        # Slice out the sentences for the windows and return with their total score
        most_positive = (scored[max_start:max_start+k], max_sum)
        most_negative = (scored[min_start:min_start+k], min_sum)
        return most_positive, most_negative
    
    # -------------------------------
    # REQUIREMENT 1: PRIMARY FUNCION
    # -------------------------------

    def analyze_sentiment(text):
        sentences = splittingPara(text)
        scored = scoringSentence(sentences)

        max_sentence, min_sentence = findingExtremeScores(scored)

        window_size = 3
        most_pos_window, most_neg_window = SLIDINGWINDOW_EFFICIENT(scored, window_size)
        most_positive_segment, most_negative_segment = arbitrary_length(scored)

        scored = scoringSentence(sentences)
        
        # Get extreme sentences
        max_sentence, min_sentence = findingExtremeScores(scored)

        return {
            "most_positive_sentence": max_sentence,
            "most_negative_sentence": min_sentence,
            "most_positive_window": most_pos_window,
            "most_negative_window": most_neg_window,
            "most_positive_segment": most_positive_segment,
            "most_negative_segment": most_negative_segment,
            "all_sentences": scored
        }
    
    # -------------------------------
    # REQUIREMENT 6: RE_INSERT SPACES AND FIND POSSIBLE VALID SEGMENTATIONS
    # -------------------------------

    def remove_spaces_and_split(txt, basedir):
        noSpaces = txt.replace(" ", "")
    # Build path to dictionary file
        wordDict = os.path.join(basedir, "2of12.txt")

        # Read the dictionary words into a set
        with open(wordDict, encoding="utf-8") as f:
            wordSet = set(word.strip().lower() for word in f if word.strip().isalpha())

        # Use the wordBreak function to split the text based on the dictionary
        wordBreakSentences = splittingNoSpace(noSpaces)
        words = wordBreak(wordBreakSentences, wordSet)

        # Join the words back with spaces
        return " ".join(words)
        
    def process_text(input_text, action, basedir):
        results = {}
        if input_text:
            if action == "Remove Space":
                cleaned_text = remove_spaces_and_split(input_text, basedir)
                results = analyze_sentiment(cleaned_text)

            elif action == "Analyze Sentiment":
                results = analyze_sentiment(input_text)

        return results

    # -------------------------------
    # CORE FUNCTIONALITIES EXECUTION STARTS HERE
    # -------------------------------
    results = {}   # Place results in dictionary to look up easily & fast
    if txt:
        results = process_text(txt, action, BASEDIR)
    elif fileTxt:
        results = process_text(fileTxt, action, BASEDIR)
        
    return render_template('review.html', 
                           txt=txt,
                           fileTxt=fileTxt, 
                           results=results)  # Passing results back into the template


if __name__ == '__main__':
    app.run(debug=True)