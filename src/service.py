import httpx
import ssl
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import dotenv_values
from datetime import datetime, timezone
from src.timed_stat_decrease import timed_stat_decrease

config = dotenv_values(".env")

app = FastAPI()

origins = [
	config.get("WILD_WAGS_HOST"),
]

app.add_middleware(
	CORSMiddleware,
	allow_origins=origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["Authorization"]
)

@app.post("/increase")
async def increase_stat(request: Request):
	try:
		body = await request.json()
		encrypted_state = body.get("state")
		stat = body.get("stat")
		auth = request.headers.get("Authorization")

		if not encrypted_state or not stat:
			return JSONResponse(status_code=400, content={"error": "Invalid request"})
		
		async with httpx.AsyncClient(verify="certificate.pem") as client:
			if not auth:
					decrypt_res = await client.get(f"{config.get('STATE_VAULT_HOST')}/decrypt", params={"state": encrypted_state})
			else:
					decrypt_res = await client.get(f"{config.get('STATE_VAULT_HOST')}/decrypt", headers={"Authorization": auth}, params={"state": encrypted_state})

			if decrypt_res.status_code != 200:
				return JSONResponse(status_code=decrypt_res.status_code, content={"error": decrypt_res.json().get("error")})

			res_data = decrypt_res.json().get("data")
			mood = res_data["pet"]["moodMeter"]

			if stat not in mood:
				return JSONResponse(status_code=400, content={"error": "Invalid request"})

			curr_stat_val = mood[stat]

			if curr_stat_val > 75:
				return JSONResponse(status_code=200, content={"message": "No stat updates"})

			updated_data = {"pet": {"moodMeter": {stat: curr_stat_val + 25}}}
			params = {"state": encrypted_state}
			headers = {"Authorization": auth} if auth else {}

			update_res = await client.post(f"{config.get('STATE_VAULT_HOST')}/update", headers=headers, params=params, json=updated_data)

			if update_res.status_code != 200:
				return JSONResponse(status_code=update_res.status_code, content={"error": update_res.json().get("error")})

			update_res_json = update_res.json()
			return JSONResponse(status_code=200, content={
				"encrypted": update_res_json.get("encrypted"),
				"data": update_res_json.get("data"),
				"quantity": 25
				})
	except:
		return JSONResponse(status_code=400, content={"error": "Invalid request"})

@app.post("/stats-decay")
async def stats_decay(request: Request):
	try:
		body = await request.json()
		encrypted_state = body.get("state")
		auth = request.headers.get("Authorization")

		if not encrypted_state:
			return JSONResponse(status_code=400, content={"error": "Invalid request"})
		
		
		async with httpx.AsyncClient(verify="certificate.pem") as client:
			if not auth:
					decrypt_res = await client.get(f"{config.get('STATE_VAULT_HOST')}/decrypt", params={"state": encrypted_state})
			else:
					decrypt_res = await client.get(f"{config.get('STATE_VAULT_HOST')}/decrypt", headers={"Authorization": auth}, params={"state": encrypted_state})

			if decrypt_res.status_code != 200:
				return JSONResponse(status_code=decrypt_res.status_code, content={"error": decrypt_res.json().get("error")})

			res_data = decrypt_res.json().get("data")
			mood = res_data["pet"]["moodMeter"]
			last_updated = datetime.fromisoformat(mood["lastStatDecrement"].replace("Z", "+00:00"))
			current_time = datetime.now(timezone.utc)
			decrease_by = timed_stat_decrease(last_updated, current_time)

			if decrease_by == 0:
				return JSONResponse(status_code=200, content={"message": "No stat updates"})

			stat_updates = {}
			for stat, val in mood.items():
				if stat != "lastStatDecrement" and val >= 25:
					new_val = val - decrease_by
					stat_updates[stat] = max(0, val - decrease_by)

			if not stat_updates:
				return JSONResponse(status_code=200, content={"message": "No stat updates"})

			stat_updates["lastStatDecrement"] = current_time.isoformat().replace("+00:00", "Z")
			updated_data = {"pet": {"moodMeter": stat_updates}}
			params = {"state": encrypted_state}
			headers = {"Authorization": auth} if auth else {}

			update_res = await client.post(f"{config.get('STATE_VAULT_HOST')}/update", headers=headers, params=params, json=updated_data)

			if update_res.status_code != 200:
				return JSONResponse(status_code=update_res.status_code, content={"error": update_res.json().get("error")})

			update_res_json = update_res.json()
			return JSONResponse(status_code=200, content={
				"encrypted": update_res_json.get("encrypted"),
				"data": update_res_json.get("data"),
				"quantity": -abs(decrease_by)
				})
	except:
		return JSONResponse(status_code=400, content={"error": "Invalid request"})


def main():
	print("\nStats Microservice running on", f"https://localhost:{config.get('PORT')}")
	uvicorn.run(
		"src.service:app",
		host="127.0.0.1",
		port=int(config.get('PORT')),
		reload=True,
		ssl_certfile="certificate.pem",
		ssl_keyfile="private-key.pem",
		log_level="warning"
		)

if __name__ == "__main__":
	main()