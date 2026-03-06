# Imports
import os
from quart import Quart, render_template, request, jsonify, send_from_directory
from quart_rate_limiter import RateLimiter, rate_limit
from datetime import timedelta
import urllib.parse
import requests
import httpx
import uvicorn


# App definition
app = Quart(__name__, template_folder="pages")
RateLimiter(app)


# Main site
@app.route("/")
async def index():
    return await render_template("index.html")


# Ask AI endpoint
@app.route("/dologic", methods=["POST"])
@rate_limit(1, timedelta(seconds=3))
async def do_logic():
    data = await request.get_json()

    syll = urllib.parse.unquote(data.get("syll", ""))
    stype = urllib.parse.unquote(data.get("type", ""))

    url = "http://127.0.0.1:51791/v1/chat/completions"
    reply = 'Something went wrong'

    if stype == 0 or stype == '0':
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={'messages': [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. A - All x are y; E - No x are y; I - Some x are y; O - Some x are not y. Check if they\'re logically correct and explain their reasoning. Common checks:\n5 Rules (Classical Method)\n1. Middle Term Distribution (M): A middle term must be distributed (appear as the predicate of a general proposition or the subject of a negative proposition) in at least one premise.\n2. Avoiding Two Negative Premises: A valid conclusion cannot be drawn from two negative premises (e.g., "Some S are not P" and "No S is P").\n3. Negative Consistency: A negative premise implies a negative conclusion (if there is a negative premise, the conclusion must be negative).\n4. Assertion Consistency: Two affirmative premises (e.g., "Every A is B") imply an affirmative conclusion.\n5. Decomposition of Terms in the Conclusion: If a term is distributed in the conclusion, it must also be distributed in the premise from which it originates (e.g., S or P). Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check this syllogism:\n{syll}\nProvide a brief, not long of a response!\nDO NOT REFER TO RULES BY THEIR NUMBERS/IDS!'}], 'max_tokens': -1}, timeout=240.0)
        reply = response.json()['choices'][0]['message']['content']
        if "</think>" in reply:
            reply = reply.split("</think>")[1].strip()
    elif stype == 1 or stype == '1':
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={'messages': [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. A - All x are y; E - No x are y; I - Some x are y; O - Some x are not y. Check if they\'re logically correct and explain their reasoning. Common checks:\n5 Rules (Classical Method)\n1. Middle Term Distribution (M): A middle term must be distributed (appear as the predicate of a general proposition or the subject of a negative proposition) in at least one premise.\n2. Avoiding Two Negative Premises: A valid conclusion cannot be drawn from two negative premises (e.g., "Some S are not P" and "No S is P").\n3. Negative Consistency: A negative premise implies a negative conclusion (if there is a negative premise, the conclusion must be negative).\n4. Assertion Consistency: Two affirmative premises (e.g., "Every A is B") imply an affirmative conclusion.\n5. Decomposition of Terms in the Conclusion: If a term is distributed in the conclusion, it must also be distributed in the premise from which it originates (e.g., S or P). Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check these syllogism premises and make a conclusion based on them:\n{syll}\nProvide a brief, not long of a response!\nDO NOT REFER TO RULES BY THEIR NUMBERS/IDS!'}], 'max_tokens': -1}, timeout=240.0)
        reply = response.json()['choices'][0]['message']['content']
        if "</think>" in reply:
            reply = reply.split("</think>")[1].strip()

    return jsonify({"result": reply})


# Access to files
@app.route("/scripts/<filename>")
async def serve_scripts(filename):
    return await send_from_directory(os.path.join(".", "scripts"), filename)

@app.route("/styles/<filename>")
async def serve_styles(filename):
    return await send_from_directory(os.path.join(".", "styles"), filename)


# Run
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=os.environ.get("MAIN_ADDR", "0.0.0.0"),
        port=51790,
        workers=4,
    )




    You are a professor of logic and your job is to evaluate syllogisms. A - All x are y; E - No x are y; I - Some x are y;
    O - Some x are not y. Check if they\'re logically correct and explain their reasoning. Common checks:\n5 Rules (Classical Method)\n
    1. Middle Term Distribution (M): A middle term must be distributed (appear as the predicate of a general proposition or the subject of a negative proposition)
    in at least one premise.\n2. Avoiding Two Negative Premises: A valid conclusion cannot be drawn from two negative premises
    (e.g., "Some S are not P" and "No S is P").\n3. Negative Consistency: A negative premise implies a negative conclusion
    (if there is a negative premise, the conclusion must be negative).\n4. Assertion Consistency: Two affirmative premises
    (e.g., "Every A is B") imply an affirmative conclusion.\n5. Decomposition of Terms in the Conclusion: If a term is distributed in the conclusion,
    it must also be distributed in the premise from which it originates (e.g., S or P). Syllogisms can have more than 2 premises.
    Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check this syllogism:
    \n{syll}\nProvide a brief, not long of a response!\nDO NOT REFER TO RULES BY THEIR NUMBERS/IDS!