from llama_client import query_llama


r = query_llama("Write a friendly one-line welcome message for customer support.", max_tokens=60)
print(r['response'])
