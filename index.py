




# hello:

import os

import chromadb
import pandas as pd
from langdetect import detect
import time


df=pd.read_csv('uber_reviews_without_reviewid.csv')
"""
print(df.head())

# Check the columns and shape of the DataFrame
print(df.columns.to_list())
print(df.shape)
"""

#clean the data now


"""

# Keep only what we need
df = df[["content", "score", "at", "thumbsUpCount"]]

# Remove empty reviews
df = df.dropna(subset=["content"])

# Remove very short reviews (noise)
df = df[df["content"].str.len() > 20]

# Convert date column convert the time
df["at"] = pd.to_datetime(df["at"])

# Reset index   it return the new ones only and drop the old ones
df = df.reset_index(drop=True)




def is_english(text):
    try:
        return detect(text) == "en"
    except:
        return False

# Filter English only
df = df[df["content"].apply(is_english)]
df = df.reset_index(drop=True)

print(f"English reviews: {len(df)}")



# save the clean data to a new CSV file
df.to_csv("uber_reviews_clean.csv", index=False)
print("✅ Clean data saved!")




print(f"Clean reviews: {len(df)}")
print(df.head())

"""




"""
dfclean = pd.read_csv("uber_reviews_clean.csv")
print(dfclean.head())

"""

#now we will move to put the data in the vector databasse chromodb


from chromadb import Client


from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Free! No API key needed
embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)





Client=chromadb.PersistentClient(path="./chroma_db")



collection = Client.get_or_create_collection(
    name="uber_reviews",
    embedding_function=embedding_function
)






# Add documents in batches to avoid memory issues to not make it evry time we run the code and to make it faster and more efficient


def add_in_batches(collection, df, batch_size=100):
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size]
        collection.add(
            documents=batch["content"].tolist(),
            ids=[str(j) for j in range(i, i + len(batch))],
            metadatas=[
                {
                    "score": int(row["score"]),
                    "date": str(row["at"]),
                    "thumbsUpCount": int(row["thumbsUpCount"])
                }
                for _, row in batch.iterrows()
            ]
        )
        print(f"✅ {min(i + batch_size, len(df))}/{len(df)} reviews added")
        time.sleep(0.5)

# Only run once
if collection.count() == 0:
    add_in_batches(collection, dfclean)
    print("🎉 All reviews embedded!")
else:
    print(f"✅ Already stored: {collection.count()} reviews")







#now we will moove chatbot we will use

from groq import Groq

client_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

response = client_groq.chat.completions.create(
    model="llama3-8b-8192",
    messages=[{"role": "user", "content": "your question"}]
)


















conversation_history = []

if len(conversation_history) > 10:
    conversation_history = conversation_history[-10:]

def chat(user_question):
    # Step 1 — Find relevant reviews from ChromaDB
    results = collection.query(
        query_texts=[user_question],
        n_results=5
    )
    relevant_reviews = results["documents"][0]

    # Step 2 — Build context from reviews
    context = "\n".join([f"- {r}" for r in relevant_reviews])

    # Step 3 — Add to conversation history
    conversation_history.append({
        "role": "user",
        "content": f"""
        Context reviews:
        {context}

        Question: {user_question}
        """
    })

    # Step 4 — Send to Groq
    response = client_groq.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {
                "role": "system",
                "content": """You are UberMind, an AI assistant that analyzes 
                Uber user reviews. Answer questions based ONLY on the reviews 
                provided. Be specific and mention numbers when possible.
                only answer based on the reviews, do not make assumptions or use outside knowledge.
                and if you don't know the answer, say you don't know.also if the question is not related to the uber reviews, say you can't answer that question.
                """
            },
            *conversation_history
        ]
    )

    # Step 5 — Get and store response
    answer = response.choices[0].message.content
    conversation_history.append({
        "role": "assistant",
        "content": answer
    })

    return answer

# Test it
print(chat("What do users complain about most?"))