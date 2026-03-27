# --- Imports ---
import os
from quart import Quart, render_template, request, jsonify, send_from_directory, Response, websocket, redirect, url_for, session
from quart_auth import QuartAuth, login_required, login_user, logout_user, current_user, AuthUser
from quart_rate_limiter import RateLimiter, rate_limit
from datetime import timedelta
import urllib.parse
import ldap3
import requests
import httpx
import ssl
import uvicorn
from datetime import datetime
import pandas as pd
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from groq import AsyncGroq, APIStatusError
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
				 'qwen/qwen3-32b',
				 'llama-3.1-8b-instant',
				 'meta-llama/llama-4-scout-17b-16e-instruct']
UPLOAD_ARCHIVE = "uploads"
GENERATED_ARCHIVE = "generated"
RESULTS_ARCHIVE = 'results'
LCPP_URL = "http://127.0.0.1:51791/v1/chat/completions"
premises_cols = ['premises', 'przesłanki', 'przeslanki', 'prem']
conclusion_cols = ['conclusion', 'conc', 'wniosek', 'wnioski', 'conclusions']
valid_cols = ['valid', 'prawdziwość', 'prawdziwosc']


# --- App definition ---
app = Quart(__name__, template_folder="pages")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
RateLimiter(app)

# --- Session reset ---
@app.before_request
def make_session_non_permanent():
	session.permanent = False

# --- LDAP Configuration ---
app.config['LDAP_HOST'] = os.environ.get('LDAP_HOST')
app.config['LDAP_PORT'] = 636
app.config['LDAP_USE_SSL'] = True
app.config['LDAP_BASE_DN'] = os.environ.get('LDAP_BASE_DN')

app.config['SECRET_KEY'] = os.environ.get('QUART_SECRET_KEY')

cert_path = '/etc/ssl/certs/ca-certificates.crt'
ca_cert_path = os.environ.get('LDAP_CA_CERTS_FILE', cert_path)
app.config['LDAP_TLS_CA_CERTS_FILE'] = ca_cert_path

app.config['LDAP_TLS_REQUIRE_CERT'] = ssl.CERT_REQUIRED

app.config['LDAP_USER_DNS'] = [dn.strip() for dn in os.environ.get('LDAP_USER_DN', '').split(';') if dn.strip()]

app.config['LDAP_USER_RDN_ATTR'] = 'uid'
app.config['LDAP_USER_LOGIN_ATTR'] = 'uid'
app.config['LDAP_USER_FULLNAME_ATTR'] = os.environ.get('LDAP_USER_FULLNAME_ATTR', 'cn')

class User(AuthUser):
	def __init__(self, identifier):
		super().__init__(identifier)
		profile = session.get('user_profile', {})
		self.username = profile.get('username')
		self.dn = profile.get('dn')
		self.data = data = profile.get('attributes', {})

	def get_id(self):
		return self.dn

	def get_fullname(self):
		return self.data.get(app.config['LDAP_USER_FULLNAME_ATTR'], [self.username])[0]
	
	@property
	def identifier(self) -> str:
		return self.username
	
login_manager = QuartAuth(app, user_class=User)
login_manager.login_view = "login"

# --- End of LDAP Configuration ---


# --- User Management ---
@app.route('/login', methods=['GET', 'POST'])
async def login():
	if await current_user.is_authenticated:
		return redirect(url_for('index'))

	if request.method == 'POST':
		form = await request.form
		username = form.get('username').lower()
		password = form.get('password')
		app.logger.info(f"Attempting login for user: {username}")

		if not username or not password:
			app.logger.warning("Login attempt with missing username or password.")
			return await render_template("auth.html", error="Missing username or password")

		conn = None
		bind_successful = False
		user_dn_for_bind = None
		base = None

		try:
			app.logger.debug("--- Manual LDAP Authentication ---")

			user_dns_to_try = app.config.get('LDAP_USER_DNS', [])
			if not user_dns_to_try:
				app.logger.error("No LDAP_USER_DN configured for user authentication.")
				return await render_template("auth.html", error="Server configuration error.")
			
			for user_base_dn in user_dns_to_try:
				user_dn = f"{app.config['LDAP_USER_LOGIN_ATTR']}={username},{user_base_dn}"
				app.logger.debug(f"Manual Auth: Constructed User DN: {user_dn}")

				tls_config = ldap3.Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)

				server = ldap3.Server(
					app.config['LDAP_HOST'],
					port=app.config['LDAP_PORT'],
					use_ssl=app.config['LDAP_USE_SSL'],
					tls=tls_config
				)
				app.logger.debug(f"Manual Auth: Connecting to server: {server.host}:{server.port} SSL={server.ssl}")

				try:
					conn = ldap3.Connection(
						server,
						user=user_dn,
						password=password,
						authentication=ldap3.SIMPLE,
						auto_bind=True
					)
					if conn.bound:
						bind_successful = True
						user_dn_for_bind = user_dn
						base = user_base_dn
						app.logger.info(f"Manual Auth: Bind SUCCESSFUL for DN: {user_dn}")
						break
					else:
						app.logger.warning(f"Manual Auth: Initial bind FAILED for DN: {user_dn}. Result: {conn.result}")
				
				except ldap3.core.exceptions.LDAPBindError as e:
					app.logger.warning(f"Manual Auth: LDAPBindError for DN: {user_dn}: {e}")
					continue
				finally:
					if conn and conn.bound and not bind_successful:
						conn.unbind()

			if bind_successful and conn:
				search_base = base
				search_filter = f"({app.config['LDAP_USER_LOGIN_ATTR']}={username})"
				attributes_to_get = [app.config['LDAP_USER_FULLNAME_ATTR'], app.config['LDAP_USER_LOGIN_ATTR']]
				app.logger.debug(f"Manual Auth: Searching for user attributes. Base='{search_base}', Filter='{search_filter}', Attrs={attributes_to_get}")

				if conn.search(search_base=search_base,
							   search_filter=search_filter,
							   search_scope=ldap3.SUBTREE,
							   attributes=attributes_to_get):

					if len(conn.entries) == 1:
						entry = conn.entries[0]
						actual_user_dn = entry.entry_dn
						app.logger.debug(f"Manual Auth: User entry found: {entry.entry_dn}")
						app.logger.debug(f"Manual Auth: User attributes: {entry.entry_attributes_as_dict}")

						user_data = {k: v[0] for k, v in entry.entry_attributes_as_dict.items() if v}

						user_attributes_dict = {k: v[0] for k, v in entry.entry_attributes_as_dict.items() if v}

						user_profile_for_session = {
							'dn': actual_user_dn,
							'username': username,
							'attributes': user_attributes_dict
						}
						session['user_profile'] = user_profile_for_session
						app.logger.debug(f"Manual Auth: Stored user profile in session for {username}")

						user = User(username)
						login_user(user)
						app.logger.info(f"User {username} object created and logged in via Flask-Login.")
						return redirect(url_for('index'))
					else:
						app.logger.error(f"Manual Auth: Search returned {len(conn.entries)} entries for filter '{search_filter}'. Expected 1.")
						return await render_template("auth.html", error="Login failed: Could not uniquely identify user.")
				else:
					app.logger.error(f"Manual Auth: Search failed after successful bind. Filter='{search_filter}'. Result: {conn.result}")
					return await render_template("auth.html", error="Login failed: Could not retrieve user data.")

			else:
				app.logger.warning(f"Manual Auth: Bind FAILED for user '{username}' against all configured DNs.")
				if conn.result and conn.result.get('result') == 49:
					return await render_template("auth.html", error="Invalid username or password")
				else:
					return await render_template("auth.html", error="LDAP bind failed (not invalid credentials).")

		except ldap3.core.exceptions.LDAPException as e:
			app.logger.error(f"Manual Auth: LDAPException during manual authentication: {e}", exc_info=True)
			return await render_template("auth.html", error="An LDAP error occurred during login.")
		except Exception as e:
			app.logger.error(f"Manual Auth: Non-LDAP Exception during manual authentication: {e}", exc_info=True)
			return await render_template("auth.html", error="An unexpected error occurred during login.")
		finally:
			if conn and conn.bound:
				conn.unbind()
			app.logger.debug("--- Finished Manual LDAP Authentication ---")

	return await render_template("auth.html")

@app.route('/logout')
@login_required
async def logout():
	session.pop('user_profile', None)
	logout_user()
	app.logger.info("User logged out.")
	return redirect(url_for('login'))

# --- End of User Management ---


# --- Main site ---
@app.route("/")
@login_required
@rate_limit(1, timedelta(seconds=2))
async def index():
	return await render_template("index.html")


# --- TODO: Jakub ---
## Czy logowanie KUL?
## Ładniejsze "Pobierz wyniki"
## Logowanie pojedynczych zapytań
## Add retrying if rpm limit
## Add more local models


async def find_col(coltype, colnames):
	for col in colnames:
		if coltype=='prem':
			if col.lower() in premises_cols:
				return col
		elif coltype=='conc':
			if col.lower() in conclusion_cols:
				return col
		elif coltype=='valid':
			if col.lower() in valid_cols:
				return col
	return coltype


# --- Process types/models function ---
async def figure_out(model, stype, syll, conc = '', reason_effort = 'none', ws = None):
	reply = 'Something went wrong.'

	messages = ""
	if stype == 0 or stype == '0':
		messages =  [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. Check if they\'re logically correct. Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check this syllogism:\n{syll}{'\n'+conc if conc !='' else ''}\nAnd respond wether it is logically (not sematically) correct.\nProvide a brief, not long of a response!'}]
	elif stype == 1 or stype == '1':
		messages =  [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. Check if they\'re logically correct. Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check this syllogism:\n{syll}{'\n'+conc if conc !='' else ''}\nAnd respond wether it is logically (not sematically) correct.\nIMPORTANT! RESPOND ONLY WITH EITHER 0 OR 1 WHERE 0 MEANS INCORRECT AND 1 MEANS CORRECT! DO NOT USE ANTHING ELSE IN YOUR RESPONSE. RESPOND ONLY WITH EITHER 0 OR 1!'}]
	elif stype == 2 or stype == '2':
		messages =  [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. A - All x are y; E - No x are y; I - Some x are y; O - Some x are not y. Check if they\'re logically correct and explain their reasoning. Common checks:\n5 Rules (Classical Method)\n1. Middle Term Distribution (M): A middle term must be distributed (appear as the predicate of a general proposition or the subject of a negative proposition) in at least one premise.\n2. Avoiding Two Negative Premises: A valid conclusion cannot be drawn from two negative premises (e.g., "Some S are not P" and "No S is P").\n3. Negative Consistency: A negative premise implies a negative conclusion (if there is a negative premise, the conclusion must be negative).\n4. Assertion Consistency: Two affirmative premises (e.g., "Every A is B") imply an affirmative conclusion.\n5. Decomposition of Terms in the Conclusion: If a term is distributed in the conclusion, it must also be distributed in the premise from which it originates (e.g., S or P). Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check these syllogism premises and make a conclusion based on them:\n{syll}\nProvide a brief, not long of a response!\nDO NOT REFER TO RULES BY THEIR NUMBERS/IDS!'}]
	elif stype == 3 or stype == '3':
		messages = [{'role': 'system', 'content': 'You are a professor of logic and your job is to evaluate syllogisms. A - All x are y; E - No x are y; I - Some x are y; O - Some x are not y. Check if they\'re logically correct and explain their reasoning. Common checks:\n5 Rules (Classical Method)\n1. Middle Term Distribution (M): A middle term must be distributed (appear as the predicate of a general proposition or the subject of a negative proposition) in at least one premise.\n2. Avoiding Two Negative Premises: A valid conclusion cannot be drawn from two negative premises (e.g., "Some S are not P" and "No S is P").\n3. Negative Consistency: A negative premise implies a negative conclusion (if there is a negative premise, the conclusion must be negative).\n4. Assertion Consistency: Two affirmative premises (e.g., "Every A is B") imply an affirmative conclusion.\n5. Decomposition of Terms in the Conclusion: If a term is distributed in the conclusion, it must also be distributed in the premise from which it originates (e.g., S or P). Syllogisms can have more than 2 premises. Sometimes a name can appear using its synonyms. Premises do not have to be in order.'}, {'role': 'user', 'content': f'Check this syllogism:\n{syll}{'\n'+conc if conc !='' else ''}\nProvide a brief, not long of a response!\nDO NOT REFER TO RULES BY THEIR NUMBERS/IDS!'}]
	elif stype == 4 or stype == '4':
		messages = [{'role': 'system', 'content': 'Jesteś pomocnym asystentem'}, {'role': 'user', 'content': f'Czy to rozumowanie jest poprawne: {syll}\nPrzedstaw krótkie wyjaśnienie swojego rozumowania.\nDodaj na końcu swojej wypowiedzi cyfrę 0 dla nieprawidłowego rozumowania lub 1 dla prawidłowego rozumowania.'}]
	else:
		messages = [{'role': 'system', 'content': f'{stype}'}, {'role': 'user', 'content': f'Sylogizm: {syll}{'\n'+conc if conc !='' else ''}'}]

	tokens = 0

	if (model in LOCAL_MODELS):
		reply = await local_prompt(messages)
	elif (model in REMOTE_MODELS):
		reply, tokens = await remote_prompt(messages, model, reason_effort, ws)
	else:
		reply += " Wrong model."

	return reply, tokens


# --- Ask AI endpoint ---
@app.route("/api/dologic", methods=["POST"])
@login_required
@rate_limit(1, timedelta(seconds=1))
async def do_logic():
	data = await request.get_json()

	syll = urllib.parse.unquote(data.get("syll", ""))
	stype = urllib.parse.unquote(data.get("type", ""))
	model = urllib.parse.unquote(data.get("model", ""))
	reason_effort = urllib.parse.unquote(data.get("effort", "none"))


	reply, tokens = await figure_out(model, stype, syll, reason_effort=reason_effort)

	if tokens > 0:
		with open('tokens.csv', 'a') as f:
			f.write(f"{tokens}, 1\n")

	return jsonify({"result": reply})


# -- Process file endpoint ---
@app.websocket("/ws/domorelogic")
@login_required
@rate_limit(1, timedelta(seconds=1))
async def do_more_logic():	
	msg = await websocket.receive_json()
	file = urllib.parse.unquote(msg.get("file", ""))
	stype = urllib.parse.unquote(msg.get("type", ""))
	model = urllib.parse.unquote(msg.get("model", ""))
	reason_effort = urllib.parse.unquote(msg.get("effort", "none"))

	await websocket.send_json({"type": "started", "file": file})
	try:
		path = os.path.join(UPLOAD_ARCHIVE if file.startswith('upload') else GENERATED_ARCHIVE, file)
		syllos = pd.read_csv(path)
		syllos['response'] = ''
		total = len(syllos)

		premcol = await find_col('prem', syllos.columns)
		conccol = await find_col('conc', syllos.columns)
		validcol = await find_col('valid', syllos.columns)

		conf = [[0, 0], [0, 0]]
		tokens_total = 0

		for i, syllo in syllos.iterrows():
			try:
				reply, tokens = await figure_out(model, stype, syllo[premcol], syllo.get(conccol, ''), reason_effort, websocket)
				if (reply != ''):
					pred = int(reply[-1]) if reply[-1].isdigit() else ""
					if pred in [0, 1, "0", "1"] and validcol in syllo:
						conf[(int(syllo[validcol])+1)%2][(pred+1)%2] += 1
				tokens_total += tokens
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
		
		with open('tokens.csv', 'a') as f:
			f.write(f"{tokens}, {total}\n")

		if conf != [[0, 0], [0, 0]]:
			n = len(conf)
			total = sum(sum(r) for r in conf)
			correct = sum(conf[i][i] for i in range(n))
			acc = (correct / total) if total else 0
			prec = [ (conf[i][i] / (sum(conf[r][i] for r in range(n)) or 1)) for i in range(n) ]
			rec = [ (conf[i][i] / (sum(conf[i]) or 1)) for i in range(n) ]
			mp = sum(prec) / n if n else 0
			mr = sum(rec) / n if n else 0
			mf = (2 * mp * mr / (mp + mr)) if (mp + mr) else 0
			await websocket.send_json({
				"type": "confusion",
				"labels": ["True", "False"],
				"matrix": conf,
				"metrics": {
					"accuracy": acc,
					"macro_precision": mp,
					"macro_recall": mr,
					"macro_f1": mf,
					"total": int(total)
				}
			})
	
		new_filename = f"result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"
		results_filepath = os.path.join(RESULTS_ARCHIVE, new_filename)
		syllos.to_csv(results_filepath, index=False)
		await websocket.send_json({"type": "done", "success": True, "file": new_filename})
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
async def remote_prompt(messages, model, reason_effort, ws = None):

	reason = True
	if reason_effort == 'none':
		reason_effort = None
		reason = False
	if model in ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'meta-llama/llama-4-scout-17b-16e-instruct']:
		reason_effort = None
		reason = None
	for i in range(1, 12):
		try:
			client = AsyncGroq(
				api_key=os.environ.get("GROQ_API_KEY"),
			)
			chat_completion = await client.chat.completions.create(
				messages=messages,
				model=model,
				include_reasoning=reason,
				reasoning_effort=reason_effort
			)
			break
		except APIStatusError as e:
			if e.status_code == 429:
				if i <= 10:
					if ws is not None:
						await ws.send_json({"type": "rate_limit", "num": i})
					await asyncio.sleep(5)
					continue
				else:
					if ws is not None:
						await ws.send_json({"type": "rate_limit_stop"})
			else:
				raise e
		except Exception as e:
			raise e

	reply = chat_completion.choices[0].message.content
	tokens = chat_completion.usage.completion_tokens
	return reply, tokens


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
		List[Dict[str, Any]]: Array of objects with premises, conclusion, and valid(sat) status.
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
	save_path = os.path.join(history_path, file_name)
	df.to_csv(save_path, index=False)

	result = []
	for _, row in df.iterrows():
		sentences = row['sentences']
		result.append({
			'premises': sentences[:-1] if len(sentences) > 1 else sentences,
			'conclusion': sentences[-1] if len(sentences) > 1 else "",
			'valid': 1 if row['sat'] == 'sat' else 0
		})

	return result


@app.route("/api/generateone", methods=["POST"])
@login_required
@rate_limit(1, timedelta(seconds=1))
async def generate_one():
	data = await request.get_json()

	minA = urllib.parse.unquote(data.get("minA", ""))
	maxA = urllib.parse.unquote(data.get("maxA", ""))

	sampling = [{"m/a": 1.0, "m/b": 3.0, "is_sat": 0.61}]
	try:
		syll = await generate_syllo(num=1, sampling=sampling, min_a=int(minA), max_a=int(maxA))
		result = "".join((prem.strip().capitalize() + (" " if prem.strip().endswith(".") else (". "))) for prem in syll[0]['premises'])
		result += syll[0]['conclusion'].strip().capitalize() + ("" if syll[0]['conclusion'].strip().endswith(".") else ("."))
		app.logger.info(f"Generated syllogism: {result}")
		return jsonify({"success": True, "result": result})
	except Exception as e:
		return jsonify({"success": False, "result": f"Error during syllogism generation: {e}"})


@app.websocket("/ws/generatemany")
@login_required
@rate_limit(1, timedelta(seconds=1))
async def generate_many():
	msg = await websocket.receive_json()
	num = urllib.parse.unquote(msg.get("num", ""))
	minA = urllib.parse.unquote(msg.get("minA", ""))
	maxA = urllib.parse.unquote(msg.get("maxA", ""))

	sampling = [{"m/a": 1.0, "m/b": 3.0, "is_sat": 0.61}]
	try:
		result = await generate_syllo(num=int(num), sampling=sampling, min_a=int(minA), max_a=int(maxA))
		for row in result:
			row['premises'] = " ".join((prem.strip().capitalize() + ("" if prem.strip().endswith(".") else ("."))) for prem in row['premises'])
			row['conclusion'] = row['conclusion'].strip().capitalize() + ("" if row['conclusion'].strip().endswith(".") else ("."))

		converted = pd.DataFrame(result)

		filename = f"gen_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"
		filepath = os.path.join(GENERATED_ARCHIVE, filename)
		converted.to_csv(filepath, index=False)

		await websocket.send_json({"type": "done", "success": True, "filename": filename})
	except Exception as e:
		await websocket.send_json({"type": "error", "error": f"Error during syllogism generation: {e}"})


# --- Access to files ---
@app.route("/scripts/<filename>")
@login_required
@rate_limit(1, timedelta(seconds=1))
async def serve_scripts(filename):
	return await send_from_directory(os.path.join(".", "scripts"), filename)

@app.route("/styles/<filename>")
@login_required
@rate_limit(1, timedelta(seconds=1))
async def serve_styles(filename):
	return await send_from_directory(os.path.join(".", "styles"), filename)

@app.route("/uploads/<filename>")
@login_required
@rate_limit(1, timedelta(seconds=1))
async def server_upload(filename):
	return await send_from_directory(os.path.join(".", "uploads"), filename)

@app.route("/results/<filename>")
@login_required
@rate_limit(1, timedelta(seconds=1))
async def server_download(filename):
	return await send_from_directory(os.path.join(".", "results"), filename)


# Upload section
@app.route('/api/upload-syllos', methods=['POST'])
@login_required
@rate_limit(1, timedelta(seconds=1))
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

@app.errorhandler(401)
async def _redirect_unauthorized(e):
	return redirect(url_for('login'))


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