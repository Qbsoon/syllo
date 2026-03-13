# --- Imports ---
import os
from quart import Quart, render_template, request, jsonify, send_from_directory, Response, websocket
from quart_rate_limiter import RateLimiter, rate_limit
from datetime import timedelta
import urllib.parse
import requests
import httpx
import uvicorn
from datetime import datetime
import pandas as pd
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from groq import Groq
import asyncio
from time import time
import traceback

# reads variables from a .env file and sets them in os.environ
load_dotenv()

# --- 'Static' values ---
LOCAL_MODELS = ['qwen3_14b_q5km']
REMOTE_MODELS = ['llama-3.3-70b-versatile', 
                 'openai/gpt-oss-20b', 
                 'openai/gpt-oss-120b', 
                 'qwen/qwen3-32b']
UPLOAD_ARCHIVE = "uploads"
LCPP_URL = "http://127.0.0.1:51791/v1/chat/completions"


# --- App definition ---
app = Quart(__name__, template_folder="pages")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
RateLimiter(app)


# --- Main site ---
@app.route("/")
async def index():
	return await render_template("index.html")


# --- TODO: Jakub ---
## Pobieranie template
## Wyświetlanie tabeli wyników + macierz pomyłek
## Czy logowanie KUL?
## Ładniejsze "Pobierz wyniki"
## Logowanie pojedynczych zapytań


# --- Process types/models function ---
async def figure_out(model, stype, syll, conc = ''):
	reply = 'Something went wrong.'

	messages = ""
	if stype == 0 or stype == '0':
		messages =  [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. Check if they\'re logically correct. Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check this syllogism:\n{syll}\nAnd respond wether it is logically (not sematically) correct.\nProvide a brief, not long of a response!'}]
	elif stype == 1 or stype == '1':
		messages =  [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. Check if they\'re logically correct. Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check this syllogism:\n{syll}\nAnd respond wether it is logically (not sematically) correct.\nIMPORTANT! RESPOND ONLY WITH EITHER 0 OR 1 WHERE 0 MEANS INCORRECT AND 1 MEANS CORRECT! DO NOT USE ANTHING ELSE IN YOUR RESPONSE. RESPOND ONLY WITH EITHER 0 OR 1!'}]
	elif stype == 2 or stype == '2':
		messages =  [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. A - All x are y; E - No x are y; I - Some x are y; O - Some x are not y. Check if they\'re logically correct and explain their reasoning. Common checks:\n5 Rules (Classical Method)\n1. Middle Term Distribution (M): A middle term must be distributed (appear as the predicate of a general proposition or the subject of a negative proposition) in at least one premise.\n2. Avoiding Two Negative Premises: A valid conclusion cannot be drawn from two negative premises (e.g., "Some S are not P" and "No S is P").\n3. Negative Consistency: A negative premise implies a negative conclusion (if there is a negative premise, the conclusion must be negative).\n4. Assertion Consistency: Two affirmative premises (e.g., "Every A is B") imply an affirmative conclusion.\n5. Decomposition of Terms in the Conclusion: If a term is distributed in the conclusion, it must also be distributed in the premise from which it originates (e.g., S or P). Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check these syllogism premises and make a conclusion based on them:\n{syll}\nProvide a brief, not long of a response!\nDO NOT REFER TO RULES BY THEIR NUMBERS/IDS!'}]
	elif stype == 3 or stype == '3':
		messages = [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. A - All x are y; E - No x are y; I - Some x are y; O - Some x are not y. Check if they\'re logically correct and explain their reasoning. Common checks:\n5 Rules (Classical Method)\n1. Middle Term Distribution (M): A middle term must be distributed (appear as the predicate of a general proposition or the subject of a negative proposition) in at least one premise.\n2. Avoiding Two Negative Premises: A valid conclusion cannot be drawn from two negative premises (e.g., "Some S are not P" and "No S is P").\n3. Negative Consistency: A negative premise implies a negative conclusion (if there is a negative premise, the conclusion must be negative).\n4. Assertion Consistency: Two affirmative premises (e.g., "Every A is B") imply an affirmative conclusion.\n5. Decomposition of Terms in the Conclusion: If a term is distributed in the conclusion, it must also be distributed in the premise from which it originates (e.g., S or P). Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check this syllogism:\n{syll}\nProvide a brief, not long of a response!\nDO NOT REFER TO RULES BY THEIR NUMBERS/IDS!'}]
	elif stype == 4 or stype == '4':
		messages = [{'role': 'system', 'content': 'Jesteś pomocnym asystentem'}, {'role': 'user', 'content': f'Czy to rozumowanie jest poprawne: {syll}\nPrzedstaw krótkie wyjaśnienie swojego rozumowania.\nDodaj na końcu swojej wypowiedzi cyfrę 0 dla nieprawidłowego rozumowania lub 1 dla prawidłowego rozumowania.'}]
	else:
		reply += " Wrong action type."

	if (model in LOCAL_MODELS):
		reply = await local_prompt(messages)
	elif (model in REMOTE_MODELS):
		reply = await remote_prompt(messages, model)
	else:
		reply += " Wrong model."

	return reply


# --- Ask AI endpoint ---
@app.route("/api/dologic", methods=["POST"])
@rate_limit(1, timedelta(seconds=3))
async def do_logic():
	data = await request.get_json()

	syll = urllib.parse.unquote(data.get("syll", ""))
	stype = urllib.parse.unquote(data.get("type", ""))
	model = urllib.parse.unquote(data.get("model", ""))

	reply = await figure_out(model, stype, syll)

	return jsonify({"result": reply})


# -- Process file endpoint ---
@app.websocket("/ws/domorelogic")
async def do_more_logic():	
	msg = await websocket.receive_json()
	file = urllib.parse.unquote(msg.get("file", ""))
	stype = urllib.parse.unquote(msg.get("type", ""))
	model = urllib.parse.unquote(msg.get("model", ""))

	await websocket.send_json({"type": "started", "file": file})
	try:
		path = os.path.join(UPLOAD_ARCHIVE, file)
		syllos = pd.read_csv(path)
		syllos['response'] = ''
		total = len(syllos)

		for i, syllo in syllos.iterrows():
			try:
				reply = await figure_out(model, stype, syllo['premises'], syllo.get('conclusion', ''))
			except Exception as e:
				app.logger.exception("ws_domorelogic: exception at idx=%d", i)
				reply = f"ERROR: {e}"
				await websocket.send_json({"type":"row_error", "idx": i, "error": str(e)})
			syllos.at[i, 'response'] = reply

			await websocket.send_json({
                "type": "progress",
                "idx": i,
                "total": total,
                "preview": str(reply)[:200]
            })
	
		syllos.to_csv("uploads/" + file)
		await websocket.send_json({"type": "done", "success": True, "file": file})
	except Exception as e:
		app.logger.exception("ws_domorelogic: fatal error")
		await websocket.send_json({"type": "error", "error": str(e)})
	finally:
		try:
			await websocket.close()
		except Exception:
			pass


# --- Local AI function ---
async def local_prompt(messages):
	async with httpx.AsyncClient() as client:
		response = await client.post(LCPP_URL, json={'messages': messages, 'max_tokens': -1}, timeout=2400.0)
	reply = response.json()['choices'][0]['message']['content']
	if "</think>" in reply:
		reply = reply.split("</think>")[1].strip()
	return reply


# --- Remote AI function ---
async def remote_prompt(messages, model):
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )

    chat_completion = client.chat.completions.create(
        messages=messages,
        model=model,
        include_reasoning=False
    )
    reply = chat_completion.choices[0].message.content
    return reply


# --- Generate syllogism function ---
from typing import Any, Dict, List, Union

async def generate_syllo(
	num: int, 
	sampling: Union[str, List[Dict[str, Any]]], 
	min_a: int, 
	max_a: int
) -> List[Dict[str, Any]]:
	"""Generates syllogisms using the NL-SAT engine and saves to history.

	Args:
		num: Number of syllogisms to generate.
		sampling: Sampling data (JSON string or list).
		min_a: Minimum unary predicates.
		max_a: Maximum unary predicates.

	Returns:
		List[Dict[str, Any]]: Array of objects with premises, conclusion, and sat status.
	"""
	from NLSAT_engine.data_construction import run_engine

	engine_path = os.path.join("NLSAT_engine")
	history_path = os.path.join(engine_path, "history")
	os.makedirs(history_path, exist_ok=True)

	# Use asyncio.to_thread to run the blocking run_engine function without blocking the event loop
	df = await asyncio.to_thread(
		run_engine, 
		num_datapoints=num, 
		sampling_data=sampling, 
		fragment="syllogistic", 
		min_a=min_a, 
		max_a=max_a
	)

	timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
	file_name = f"{timestamp}.csv"
	df.to_csv(os.path.join(history_path, file_name), index=False)

	result = []
	for _, row in df.iterrows():
		sentences = row['sentences']
		result.append({
			'premises': sentences[:-1] if len(sentences) > 1 else sentences,
			'conclusion': sentences[-1] if len(sentences) > 1 else "",
			'sat': 1 if row['sat'] == 'sat' else 0
		})

	return result


# --- Access to files ---
@app.route("/scripts/<filename>")
async def serve_scripts(filename):
	return await send_from_directory(os.path.join(".", "scripts"), filename)

@app.route("/styles/<filename>")
async def serve_styles(filename):
	return await send_from_directory(os.path.join(".", "styles"), filename)

@app.route("/uploads/<filename>")
async def server_download(filename):
	return await send_from_directory(os.path.join(".", "uploads"), filename)


# Upload section
@app.route('/api/upload-syllos', methods=['POST'])
async def upload_file():

	files = await request.files
	if 'sylloFile' not in files:
		return jsonify({"success": False, "error": "No syllogism file part in the request"}), 400
	file = files['sylloFile']

	if file.filename == '':
		return jsonify({"success": False, "error": "No selected file"}), 400

	allowed_extensions = ['csv']
	original_filename = secure_filename(file.filename)
	file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''

	if not file_ext or file_ext not in allowed_extensions:
		return jsonify({"success": False, "error": "Invalid file type. Only CSV allowed."}), 400

	os.makedirs(UPLOAD_ARCHIVE, exist_ok=True)

	new_filename = f"upload_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{file_ext}"

	upload_filepath = os.path.join(UPLOAD_ARCHIVE, new_filename)

	try:
		await file.save(upload_filepath)
		return jsonify({"success": True, "filename": new_filename})
	except Exception as e:
		return jsonify({"success": False, "error": "Server error while saving the file."}), 500
	

# --- Error Handlers ---
@app.errorhandler(413)
async def request_entity_too_large(error):
	app.logger.warning(f"Upload failed: File too large (413). Limit is {app.config.get('MAX_CONTENT_LENGTH') / (1024*1024)}MB.")
	return jsonify(success=False, error="File is too large. Please upload a file smaller than {}MB.".format(app.config.get('MAX_CONTENT_LENGTH') // (1024*1024)), limit=app.config.get('MAX_CONTENT_LENGTH') // (1024*1024)), 413


# --- Run ---
if __name__ == "__main__":
	uvicorn.run(
		"app:app",
		host=os.environ.get("MAIN_ADDR"),
		port=51790,
		workers=4,
		timeout_keep_alive=36000,
		timeout_graceful_shutdown=36000,
	)