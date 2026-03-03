from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from dotenv import dotenv_values
from datetime import datetime, timezone
from src.timed_stat_decrease import timed_stat_decrease

config = dotenv_values(".env")

app = FastAPI()

@app.post("/increase")
def increase_stat(stat):
	return {}

@app.post("/stats-decay")
async def stats_decay(request):
	body = await request.json()
	auth = request.headers.get("Authorization")

	if not body:
		return JSONResponse(status_code=400, content={"error": "Invalid request"})
	
	encrypted_state = body.get("state")
	
	if not auth:
		async with httpx.AsyncClient() as client:
			decrypt_res = await client.get(f"{config.get('STATE_VAULT_HOST')}/decrypt", params={"state": encrypted_state})
	else:
		async with httpx.AsyncClient() as client:
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

	stat_updates["lastStatDecrement"] = now.isoformat()
	updated_data = {"pet": {"moodMeter": stat_updates}}
	params = {"state": encrypted_state}
	headers = {"Authorization": auth} if auth else {}

	update_res = await client.post(f"{config.get('STATE_VAULT_HOST')}/update", headers=headers, params=params, json=updated_data)

	return update_res.json()


def main():
	print("\nStats Microservice running in:\n")
	print(f"https://localhost:{config.get('PORT')}")