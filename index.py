




# hello:

import os
import chromadb
from dotenv import load_dotenv
import pandas as pd

import time

load_dotenv()   
from groq import Groq

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import tiktoken
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from groq import RateLimitError

"""
df=pd.read_csv('uber_reviews_without_reviewid.csv')
"""
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
    dfclean = pd.read_csv("uber_reviews_clean.csv")
    add_in_batches(collection, dfclean)
    print("🎉 All reviews embedded!")
else:
    print(f"✅ Already stored: {collection.count()} reviews")







#now we will moove chatbot we will use




client_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))












def count_tokens(text):
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))







conversation_history = []




@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(min=2, max=10),
    stop=stop_after_attempt(3)
)
def chat(user_question):
    # Step 1 — Find relevant reviews from ChromaDB

    try:
        global conversation_history


        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]




            # Detect question intent and apply filter
        question_lower = user_question.lower()

        if any(w in question_lower for w in ["support", "customer service", "help", "complaint"]):
            n_results = 8
              # mixed reviews for balance
            # Simple yes/no questions → fewer results
        elif any(w in question_lower for w in ["is", "does", "can", "will"]):
            n_results = 5

        # Complex analysis questions → more results
        else:
            n_results = 10






        if any(w in question_lower for w in ["support", "customer service", "help", "complaint"]):
            where = {"score": {"$lte": 3}}
        elif any(w in question_lower for w in ["complain", "hate", "bad", "worst", "angry", "problem"]):
            where = {"score": {"$lte": 2}}      # only angry users

        elif any(w in question_lower for w in ["love", "great", "best", "praise", "good"]):
            where = {"score": {"$gte": 4}}      # only happy users

        elif any(w in question_lower for w in ["churn", "leaving", "switching", "cancel"]):
            where = {"score": {"$lte": 2}}      # churn = angry users

        else:
            where = None









        results = collection.query(
            query_texts=[user_question],
            n_results=n_results,
            where=where
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
        model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
"content": """You are UberMind, an AI that analyzes real Uber user reviews from December 2024.

Rules:
- Answer ONLY from the reviews provided
- If question is unrelated to Uber, say: "I can only answer questions about Uber reviews"
- If unsure, say: "I don't have enough reviews to answer this"

Format every answer exactly like this:
Based on [N] reviews:
- [point 1]
- [point 2]  
- [point 3 max]

Real user: "[exact quote]"

Bottom line: [one sentence conclusion]

Strict rules:
- Max 4 bullet points
- One quote only
- Never contradict yourself
- Never label negative quote as positive
- No intro, go straight to answer

                    """
                },
                *conversation_history
            ],max_tokens=200
        )

        # Step 5 — Get and store response
        answer = response.choices[0].message.content
        conversation_history.append({
            "role": "assistant",
            "content": answer
        })

        return answer
    except Exception as e:
        return f"Error: {str(e)}"










#dashboard of the admin



def generate_insights():  # ← no parameter needed
    complaints = chat("What are the top 5 complaints?")
    praise = chat("What do users love most?")
    churn = chat("Which users are thinking about leaving?")
    features = chat("What features do users request most?")
    
    return {
        "complaints": complaints,
        "praise": praise,
        "churn": churn,
        "features": features
    }








