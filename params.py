import os

PUNCTUATION = [".", "!", "?"]
NO_CUT = (".", "!", "?", ";", ",", "'", "-", "%")
NO_CUT_WORDS = ["Dr.", "Mr.", "Mrs.", "Ms."]

MAX_DURATION_SECONDS = 120
max_duration = 20  # макс длина предложения
max_symbols = 10
# max_symbols = 20
max_word_duration = 3 #макс длина слова в секундах
min_word_duration = 0.1 #мин длина слова в секундах
ending_delay = 0.1  # дополнительное время в секундах в конце шорта, чтобы не обрезались слова

gpt_model = "gpt-4-turbo-preview"  # ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo-0125"]

gpt_params = {"gpt-4-turbo-preview":{"rpm":10000, "tpm":450000, "input_price":0.01, "output_price":0.03, "context_window":128000},
             "gpt-4":{"rpm":10000, "tpm":300000, "input_price":0.03, "output_price":0.06, "context_window":8192},
             "gpt-3.5-turbo-0125":{"rpm":10000, "tpm":1000000, "input_price":0.0005, "output_price":0.0015, "context_window":16385}}