from transformers import pipeline, BertTokenizer, BertForTokenClassification
import torch
import os
import json

class ChineseWordSegmentation:
    def __init__(self):
        print("loading word segmentation model")

        path = "AimanGh/bert-base-chinese-word-segmentation"

        # Load model and tokenizer
        self.tokenizer = BertTokenizer.from_pretrained(path)
        self.model = BertForTokenClassification.from_pretrained(path)
        self.id2label = {i: label for i, label in enumerate(["B", "I"])}

    def segment_sentence(self, sentence):
        """
        Segment a single sentence using the fine-tuned model, excluding special tokens.
        """

        # Tokenize the input sentence
        inputs = self.tokenizer(sentence, return_tensors="pt", is_split_into_words=False)
        # inputs = {key: value.to(device) for key, value in inputs.items()}

        # Get model predictions
        with torch.no_grad():
            outputs = self.model(**inputs)

        logits = outputs.logits
        predictions = torch.argmax(logits, dim=-1).squeeze().tolist()
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"].squeeze().tolist())
        labels = [self.id2label[pred] for pred in predictions]

        # remove special tokens 
        filtered_tokens = tokens[1:-1]
        filtered_labels = labels[1:-1]

        # combine tokens into segmented sentence
        words = [""]
        for token, label in zip(filtered_tokens, filtered_labels):
            if token == "[UNK]": pass
            elif token.startswith("##"):  # Handle subwords
                words[-1] += token[2:]
            else:
                if label == "B" and words[-1]:  # add a space before a new word
                    words.append("")
                words[-1] += token

        return words

def collect_files(directory_path) -> list[str]:
    files = []
    with os.scandir(directory_path) as entries:
        for entry in entries:
            if entry.is_file():
                files.append(entry.name)
    return files

def generate_output_json(in_file_path: str, segmentation: ChineseWordSegmentation, classifier: pipeline) -> list[dict]:
    with open(in_file_path, "r", encoding="utf-8") as in_file:
        data = in_file.read()

    print(f"analyzing file, {in_file_path}")
    words = segmentation.segment_sentence(data)
    results = []
    for word in words:
        output = classifier(word)
        results.append({"word": word, "output": output})
    return results

if __name__ == "__main__":
    input_dir = "inputs/"
    in_files = collect_files(input_dir)
    results = []
    if in_files:
        segmentation = ChineseWordSegmentation()
        print("loading sentiment analysis pipeline")
        classifier = pipeline("sentiment-analysis", model="tabularisai/multilingual-sentiment-analysis")
        for in_file in in_files:
            basename, extension = os.path.splitext(in_file)
            results += generate_output_json(input_dir + in_file, segmentation, classifier)

    out_file_path = "sentiment_data.js"
    with open(out_file_path, "w", encoding="utf-8") as out_file:
        out_file.write("const sentiment_data = ")
        json.dump(results, out_file, ensure_ascii=False)