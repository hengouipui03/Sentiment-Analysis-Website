# Function to split a long string into words that exist in the dictionary
def wordBreak(sentences, wordSet):
    i = 0
    first = True                  # Start at the first sentence of the text
    result = []                   # This will hold the words we find
    for sentence in sentences:
        if not first:
            result.append(".")  # Add full stop only after the first iteration
        else:
            first = False       # Mark that first iteration is done        
        sentence = sentence.lower()  # Convert to lowercase for matching
        n = len(sentence)          # Total number of characters in the text
        max_len = max(len(word) for word in wordSet)  # Length of longest word in the dictionary

        # Go through the text one character at a time
        while i < n: # i has to greater than n at some point to stop the loop
            match = None  # This will hold the word we find starting at position i

            for j in range(min(n, i + max_len), i, -1):  # Start from longest possible substring
                w = sentence[i:j]  # Get a substring from i to j
                if w in wordSet:  # Check if this substring is a word in the dictionary
                    match = w     # If yes, we found a match
                    break         # Stop looking for shorter words

            if match:
                result.append(match)  # Add the found word to the result list
                i += len(match)       # Move forward by the length of the found word
            else:
                i += 1  # If no word is found, skip one character and try again

    return result  # Return the list of words we found